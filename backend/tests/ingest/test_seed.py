"""Tests for loading the career boards and for skipping the seed when nothing changed."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ingest_source import IngestSource
from seed import __main__ as seed_main
from seed import job_boards


def _session_factory(session: AsyncSession):  # type: ignore[no-untyped-def]
    @asynccontextmanager
    async def factory() -> AsyncIterator[AsyncSession]:
        yield session

    return factory


@pytest.mark.asyncio
async def test_boards_load_in_one_go_and_rerun_safely(db_session: AsyncSession) -> None:
    with patch.object(job_boards, "AsyncSessionLocal", _session_factory(db_session)):
        await job_boards.seed_job_boards()
        first = await db_session.scalar(select(func.count()).select_from(IngestSource))

        # A board that moved to another system gets pointed at the new one and unpaused
        await db_session.execute(
            update(IngestSource)
            .where(IngestSource.name == "Job Bank jobs (Government of Canada)")
            .values(adapter_type="rss", auto_paused=True, consecutive_failures=3)
        )
        await job_boards.seed_job_boards()
        second = await db_session.scalar(select(func.count()).select_from(IngestSource))

    assert first is not None and first > 1000
    assert second == first
    jobbank = await db_session.scalar(
        select(IngestSource).where(IngestSource.name == "Job Bank jobs (Government of Canada)")
    )
    assert jobbank is not None
    await db_session.refresh(jobbank)
    assert (jobbank.adapter_type, jobbank.auto_paused) == ("jobbank", False)
    assert jobbank.config == {}  # the adapter's own list of searches


def test_fingerprint_follows_the_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SEED_SAMPLE_POSTINGS", raising=False)
    monkeypatch.delenv("ADZUNA_APP_KEY", raising=False)
    plain = seed_main.fingerprint()
    assert seed_main.fingerprint() == plain

    monkeypatch.setenv("SEED_SAMPLE_POSTINGS", "true")
    assert seed_main.fingerprint() != plain

    # Changing an API key itself never changes the fingerprint, only setting one does
    monkeypatch.setenv("ADZUNA_APP_KEY", "one")
    with_key = seed_main.fingerprint()
    monkeypatch.setenv("ADZUNA_APP_KEY", "two")
    assert seed_main.fingerprint() == with_key
