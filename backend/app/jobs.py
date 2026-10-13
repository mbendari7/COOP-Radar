"""
Background jobs that run inside the web server, so there is no extra worker or queue to host.

enqueue(job, *args)  starts a job without making the request wait and logs any error
scheduler()          starts with the app. Every 10 minutes it imports each career board
                     that has not run in INGEST_INTERVAL_HOURS (6 by default), one at a
                     time, and clears old sessions. On a brand new site the first pass
                     imports every board so real jobs show up a minute or two after start.

Only three jobs run at once so a big import cannot hog the database connections
that page requests need.
"""

import asyncio
import logging
import os
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.config import get_settings

logger = logging.getLogger(__name__)

INGEST_INTERVAL = timedelta(hours=float(os.getenv("INGEST_INTERVAL_HOURS", "6")))
_CHECK_EVERY_SECONDS = 600
_MAX_CONCURRENT_JOBS = 3

_tasks: set[asyncio.Task[None]] = set()  # keep running tasks so they are not garbage collected
_slots: asyncio.Semaphore | None = None


async def _run_source(source_id: str, run_id: str | None = None) -> None:
    from app.ingest.runner import run_source

    await run_source(UUID(source_id), UUID(run_id) if run_id else None)


async def _embed_posting(posting_id: str) -> None:
    from app.ingest.embed import embed_one

    await embed_one(UUID(posting_id))


JOBS: dict[str, Callable[..., Awaitable[None]]] = {
    "run_source": _run_source,
    "embed_posting": _embed_posting,
}


async def _run(name: str, args: tuple[str, ...]) -> None:
    global _slots
    if _slots is None:
        _slots = asyncio.Semaphore(_MAX_CONCURRENT_JOBS)
    async with _slots:
        try:
            await JOBS[name](*args)
        except Exception:  # noqa: BLE001 a failed job should never take down the server
            logger.exception("Background job %s%s failed", name, args)


def enqueue(name: str, *args: str) -> None:
    """
    Start job `name` in the background. Call it from async code like any request handler.
    Raises KeyError for a job we do not know and RuntimeError outside an event loop.
    """
    if name not in JOBS:
        raise KeyError(name)
    task = asyncio.get_running_loop().create_task(_run(name, args))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


async def _due_source_ids() -> list[str]:
    """Ids of sources that are on, not paused and have not run within INGEST_INTERVAL."""
    from sqlalchemy import or_, select

    from app.db import AsyncSessionLocal
    from app.models.ingest_source import IngestSource

    cutoff = datetime.now(UTC) - INGEST_INTERVAL
    async with AsyncSessionLocal() as db:
        stmt = select(IngestSource.id).where(
            IngestSource.enabled.is_(True),
            IngestSource.auto_paused.is_(False),
            or_(IngestSource.last_run_at.is_(None), IngestSource.last_run_at < cutoff),
        )
        return [str(i) for i in (await db.execute(stmt)).scalars().all()]


async def run_due_sources() -> int:
    """Import every source that is due, one after another. Gives back how many ran."""
    source_ids = await _due_source_ids()
    for source_id in source_ids:
        logger.info("Scheduled import for source %s", source_id)
        await _run("run_source", (source_id,))
    return len(source_ids)


async def scheduler(store: object | None = None) -> None:
    """Runs until shutdown. Clears expired keys out of `store` every round."""
    if get_settings().openai_api_key:
        await _backfill_embeddings()
    while True:
        try:
            await run_due_sources()
            purge = getattr(store, "purge_expired", None)
            if purge is not None:
                await purge()
        except Exception:  # noqa: BLE001 keep the scheduler going no matter what
            logger.exception("Scheduler cycle failed")
        await asyncio.sleep(_CHECK_EVERY_SECONDS)


async def _backfill_embeddings() -> None:
    """With smart search on, embed postings that have no vector yet, like after adding a key."""
    from app.db import AsyncSessionLocal
    from app.ingest.embed import backfill

    try:
        async with AsyncSessionLocal() as db:
            count = await backfill(db)
        logger.info("Embedded %d postings", count)
    except Exception:  # noqa: BLE001
        logger.exception("Embedding backfill failed")
