"""Tests for run_source runner using a fixture-backed adapter mock."""

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingest.base import AdapterError, RawPosting
from app.ingest.runner import _execute_run
from app.models.ingest_run import IngestRun
from app.models.ingest_source import IngestSource
from app.models.posting import Posting

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "ingest"


def _make_raw_postings() -> list[RawPosting]:
    data = json.loads((FIXTURE_DIR / "acme_jobs.json").read_text())
    from datetime import date
    return [
        RawPosting(
            title=item["title"],
            company=item["company"],
            city=item["city"],
            term=item["term"],
            work_mode=item.get("work_mode"),
            deadline=date.fromisoformat(item["deadline"]),
            description=item.get("description", ""),
            skills=item.get("skills", []),
            source_ref=item["id"],
            source_url=None,
        )
        for item in data
    ]


async def _create_source(db: AsyncSession) -> IngestSource:
    source = IngestSource(
        name="Acme Test Source",
        adapter_type="json_api",
        config={"url": "https://acme.example.com/jobs"},
    )
    db.add(source)
    await db.flush()
    return source


@pytest.mark.asyncio
async def test_first_run_adds_postings(db_session: AsyncSession):
    """First run with 5 fixture postings should add 5 new rows."""
    source = await _create_source(db_session)
    raw = _make_raw_postings()

    with patch("app.ingest.runner.adapter_for") as mock_adapter_for:
        mock_adapter = AsyncMock()
        mock_adapter.fetch = AsyncMock(return_value=raw)
        mock_adapter_for.return_value = mock_adapter

        await _execute_run(db_session, source.id)

    run_stmt = select(IngestRun).where(IngestRun.source_id == source.id)
    run = (await db_session.execute(run_stmt)).scalar_one()

    assert run.status == "success"
    assert run.added == 5
    assert run.errors == 0


@pytest.mark.asyncio
async def test_second_run_adds_zero(db_session: AsyncSession):
    """Running the same fixture data twice should add 0 on the second run."""
    source = await _create_source(db_session)
    raw = _make_raw_postings()

    with patch("app.ingest.runner.adapter_for") as mock_af:
        mock_a = AsyncMock()
        mock_a.fetch = AsyncMock(return_value=raw)
        mock_af.return_value = mock_a
        await _execute_run(db_session, source.id)

    with patch("app.ingest.runner.adapter_for") as mock_af2:
        mock_a2 = AsyncMock()
        mock_a2.fetch = AsyncMock(return_value=raw)
        mock_af2.return_value = mock_a2
        await _execute_run(db_session, source.id)

    runs_stmt = select(IngestRun).where(IngestRun.source_id == source.id).order_by(IngestRun.started_at)
    runs = (await db_session.execute(runs_stmt)).scalars().all()
    assert len(runs) == 2
    second_run = runs[1]
    assert second_run.added == 0


@pytest.mark.asyncio
async def test_removed_posting_gets_closed_at(db_session: AsyncSession):
    """A posting absent from the second run has closed_at set."""
    source = await _create_source(db_session)
    raw = _make_raw_postings()

    with patch("app.ingest.runner.adapter_for") as mock_af:
        mock_a = AsyncMock()
        mock_a.fetch = AsyncMock(return_value=raw)
        mock_af.return_value = mock_a
        await _execute_run(db_session, source.id)

    # Remove first posting from batch
    raw_minus_one = raw[1:]
    with patch("app.ingest.runner.adapter_for") as mock_af2:
        mock_a2 = AsyncMock()
        mock_a2.fetch = AsyncMock(return_value=raw_minus_one)
        mock_af2.return_value = mock_a2
        await _execute_run(db_session, source.id)

    # The first posting (acme-001) should now have closed_at set
    stmt = select(Posting).where(Posting.source_ref == "acme-001")
    posting = (await db_session.execute(stmt)).scalar_one_or_none()
    assert posting is not None
    assert posting.closed_at is not None


@pytest.mark.asyncio
async def test_adapter_error_sets_failed_status(db_session: AsyncSession):
    """AdapterError from the adapter sets IngestRun status='failed' and increments failures."""
    source = await _create_source(db_session)

    with patch("app.ingest.runner.adapter_for") as mock_af:
        mock_a = AsyncMock()
        mock_a.fetch = AsyncMock(side_effect=AdapterError("HTTP 503"))
        mock_af.return_value = mock_a
        await _execute_run(db_session, source.id)

    run_stmt = select(IngestRun).where(IngestRun.source_id == source.id)
    run = (await db_session.execute(run_stmt)).scalar_one()
    assert run.status == "failed"
    assert run.errors >= 1

    await db_session.refresh(source)
    assert source.consecutive_failures == 1


@pytest.mark.asyncio
async def test_three_consecutive_failures_auto_pause(db_session: AsyncSession):
    """After 3 consecutive failures, source.auto_paused becomes True."""
    source = await _create_source(db_session)

    for _ in range(3):
        with patch("app.ingest.runner.adapter_for") as mock_af:
            mock_a = AsyncMock()
            mock_a.fetch = AsyncMock(side_effect=AdapterError("connection refused"))
            mock_af.return_value = mock_a
            await _execute_run(db_session, source.id)

    await db_session.refresh(source)
    assert source.auto_paused is True
    assert source.consecutive_failures >= 3
