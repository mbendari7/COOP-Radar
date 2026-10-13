"""Tests for the run_source runner with a fake adapter reading test files."""

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

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
    """The first run with 5 test jobs should add 5 new rows."""
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
    """Running the same data twice should add nothing the second time."""
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
    """A job missing from the second run gets closed_at set."""
    source = await _create_source(db_session)
    raw = _make_raw_postings()

    with patch("app.ingest.runner.adapter_for") as mock_af:
        mock_a = AsyncMock()
        mock_a.fetch = AsyncMock(return_value=raw)
        mock_af.return_value = mock_a
        await _execute_run(db_session, source.id)

    # Take the first job out of the batch
    raw_minus_one = raw[1:]
    with patch("app.ingest.runner.adapter_for") as mock_af2:
        mock_a2 = AsyncMock()
        mock_a2.fetch = AsyncMock(return_value=raw_minus_one)
        mock_af2.return_value = mock_a2
        await _execute_run(db_session, source.id)

    # The first job (acme-001) should now have closed_at set
    stmt = select(Posting).where(Posting.source_ref == "acme-001")
    posting = (await db_session.execute(stmt)).scalar_one_or_none()
    assert posting is not None
    assert posting.closed_at is not None


@pytest.mark.asyncio
async def test_adapter_error_sets_failed_status(db_session: AsyncSession):
    """An AdapterError marks the IngestRun as failed and counts one more failure."""
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
    """After 3 failures in a row source.auto_paused turns True."""
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


@pytest.mark.asyncio
async def test_rerun_updates_and_never_closes_unchanged_postings(db_session: AsyncSession):
    """Rerunning a feed that did not change used to skip every row as a duplicate and then close them all."""
    source = await _create_source(db_session)
    raw = _make_raw_postings()

    for _ in range(2):
        with patch("app.ingest.runner.adapter_for") as mock_af:
            mock_a = AsyncMock()
            mock_a.fetch = AsyncMock(return_value=raw)
            mock_af.return_value = mock_a
            await _execute_run(db_session, source.id)

    runs = (
        await db_session.execute(
            select(IngestRun).where(IngestRun.source_id == source.id).order_by(IngestRun.started_at)
        )
    ).scalars().all()
    assert (runs[1].added, runs[1].updated, runs[1].closed) == (0, 5, 0)
    still_open = (
        await db_session.execute(
            select(Posting).where(Posting.source_id == source.id, Posting.closed_at.is_(None))
        )
    ).scalars().all()
    assert len(still_open) == 5


@pytest.mark.asyncio
async def test_run_reuses_triggered_run_record(db_session: AsyncSession):
    """Run now makes the run row and the worker has to finish that row and not make a second one."""
    source = await _create_source(db_session)
    run = IngestRun(source_id=source.id, started_at=datetime.now(UTC), status="running")
    db_session.add(run)
    await db_session.flush()

    with patch("app.ingest.runner.adapter_for") as mock_af:
        mock_a = AsyncMock()
        mock_a.fetch = AsyncMock(return_value=_make_raw_postings())
        mock_af.return_value = mock_a
        new_ids = await _execute_run(db_session, source.id, run.id)

    runs = (
        await db_session.execute(select(IngestRun).where(IngestRun.source_id == source.id))
    ).scalars().all()
    assert len(runs) == 1
    assert runs[0].status == "success"
    assert runs[0].added == 5
    assert len(new_ids) == 5


@pytest.mark.asyncio
async def test_run_stores_country_and_what_the_posting_asks_for(db_session: AsyncSession):
    source = await _create_source(db_session)
    raw = RawPosting(
        title="Hardware Intern", company="Acme", city="Austin", province="TX", country="US",
        term="Summer 2027", source_ref="hw-1",
        description="Pursuing a degree in Electrical Engineering, graduating in 2027 or 2028.",
    )

    with patch("app.ingest.runner.adapter_for") as mock_af:
        mock_af.return_value.fetch = AsyncMock(return_value=[raw])
        await _execute_run(db_session, source.id)

    posting = (
        await db_session.execute(select(Posting).where(Posting.source_ref == "hw-1"))
    ).scalar_one()
    assert posting.country == "US"
    assert posting.fields_of_study == ["engineering", "electrical"]
    assert posting.grad_years == [2027, 2028]


@pytest.mark.asyncio
async def test_rerun_refreshes_the_location(db_session: AsyncSession):
    """A location fixed on the board, or read better by us, replaces the old one on the next run."""
    source = await _create_source(db_session)

    def raw(city: str, province: str) -> RawPosting:
        return RawPosting(
            title="Data Intern", company="Acme", city=city, province=province, country="US",
            term="Summer 2027", description="d", source_ref="loc-1",
        )

    for city, province in (("Hybrid", "NY"), ("New York", "NY")):
        with patch("app.ingest.runner.adapter_for") as mock_af:
            mock_af.return_value.fetch = AsyncMock(return_value=[raw(city, province)])
            await _execute_run(db_session, source.id)

    posting = (
        await db_session.execute(select(Posting).where(Posting.source_ref == "loc-1"))
    ).scalar_one()
    assert (posting.city, posting.province) == ("New York", "NY")


@pytest.mark.asyncio
async def test_rerun_refreshes_the_employer_name(db_session: AsyncSession):
    """Jobs first saved under a board label get the clean employer name on the next run."""
    source = await _create_source(db_session)

    def raw(company: str) -> RawPosting:
        return RawPosting(
            title="Analog Intern", company=company, city="Toronto", province="ON", country="CA",
            term="Summer 2027", description="d", source_ref="co-1",
        )

    for company in ("Astera Labs Early Career - North America 2027", "Astera Labs"):
        with patch("app.ingest.runner.adapter_for") as mock_af:
            mock_af.return_value.fetch = AsyncMock(return_value=[raw(company)])
            await _execute_run(db_session, source.id)

    posting = (
        await db_session.execute(select(Posting).where(Posting.source_ref == "co-1"))
    ).scalar_one()
    assert posting.company == "Astera Labs"
