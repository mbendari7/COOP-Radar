"""
RQ worker entry point plus a tiny built-in scheduler.

Run with:
  python -m app.worker

This process:
  1. Connects to Redis synchronously (RQ requires a sync connection)
  2. Starts a daemon thread that, every 10 minutes, enqueues `run_source` for each
     enabled, non-paused source whose last run is older than INGEST_INTERVAL_HOURS
     (default 6). Sources are re-read each cycle, so new sources are picked up
     without a restart.
  3. Runs the RQ worker, which executes ingest and embedding jobs from the queue.
"""

import asyncio
import logging
import os
import threading
import time
from datetime import UTC, datetime, timedelta

import redis
from rq import Queue, Worker

from app.config import get_settings

logger = logging.getLogger(__name__)

QUEUE_NAME = "ingest"
INGEST_INTERVAL = timedelta(hours=float(os.getenv("INGEST_INTERVAL_HOURS", "6")))
_CHECK_EVERY_SECONDS = 600


def get_redis_connection() -> redis.Redis:
    return redis.Redis.from_url(get_settings().redis_url)


def create_queue(conn: redis.Redis | None = None) -> Queue:
    return Queue(QUEUE_NAME, connection=conn or get_redis_connection())


async def _due_source_ids() -> list[str]:
    """IDs of enabled, non-paused sources that haven't run within INGEST_INTERVAL."""
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


def enqueue_due_sources(queue: Queue) -> int:
    """Enqueue one run per due source. Returns how many jobs were enqueued."""
    source_ids = asyncio.run(_due_source_ids())
    for source_id in source_ids:
        # job_id dedupes: a source never has two queued runs at once
        queue.enqueue(
            "app.ingest.runner.run_source", source_id, job_id=f"ingest-{source_id}"
        )
        logger.info("Enqueued scheduled ingest for source %s", source_id)
    return len(source_ids)


def _scheduler_loop(queue: Queue) -> None:
    while True:
        try:
            enqueue_due_sources(queue)
        except Exception as exc:  # noqa: BLE001 — keep the scheduler alive
            logger.warning("Scheduler cycle failed: %s", exc)
        time.sleep(_CHECK_EVERY_SECONDS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    conn = get_redis_connection()
    queue = create_queue(conn)

    threading.Thread(target=_scheduler_loop, args=(queue,), daemon=True).start()

    Worker([queue], connection=conn).work()
