"""
RQ worker entry point and scheduler setup.

Run with:
  python -m app.worker

This module:
  1. Connects to Redis synchronously (RQ requires sync connection)
  2. Creates the 'ingest' queue
  3. Starts rq-scheduler to enqueue run_source for each active source every 6 hours
  4. Starts the RQ worker
"""

import os
import logging

import redis
from rq import Queue, Worker
from rq_scheduler import Scheduler  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QUEUE_NAME = "ingest"
SCHEDULE_INTERVAL = 6 * 60 * 60  # 6 hours in seconds


def get_redis_connection() -> redis.Redis:  # type: ignore[type-arg]
    return redis.from_url(REDIS_URL)


def create_queue(conn: redis.Redis | None = None) -> Queue:  # type: ignore[type-arg]
    if conn is None:
        conn = get_redis_connection()
    return Queue(QUEUE_NAME, connection=conn)


def schedule_sources(conn: redis.Redis) -> None:  # type: ignore[type-arg]
    """
    Enqueue run_source for all enabled, non-paused sources on a 6-hour schedule.
    This is called once at worker startup; rq-scheduler handles recurring runs.
    """
    import asyncio
    from app.db import AsyncSessionLocal
    from app.models.ingest_source import IngestSource
    from sqlalchemy import select

    scheduler = Scheduler(queue_name=QUEUE_NAME, connection=conn)
    queue = create_queue(conn)

    async def _get_sources() -> list[IngestSource]:
        async with AsyncSessionLocal() as db:
            stmt = select(IngestSource).where(
                IngestSource.enabled.is_(True),
                IngestSource.auto_paused.is_(False),
            )
            return list((await db.execute(stmt)).scalars().all())

    sources = asyncio.run(_get_sources())

    for source in sources:
        job_id = f"ingest-{source.id}"
        # Cancel any existing scheduled job for this source to avoid duplicates
        try:
            scheduler.cancel(job_id)
        except Exception:
            pass

        scheduler.schedule(
            scheduled_time=None,  # type: ignore[arg-type]  # start immediately
            func="app.ingest.runner.run_source",
            args=[str(source.id)],
            interval=SCHEDULE_INTERVAL,
            repeat=None,  # repeat forever
            queue_name=QUEUE_NAME,
            id=job_id,
        )
        logger.info("Scheduled ingest for source %s (%s)", source.id, source.name)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    conn = get_redis_connection()
    queue = create_queue(conn)

    try:
        schedule_sources(conn)
    except Exception as exc:
        logger.warning("Could not schedule sources at startup: %s", exc)

    worker = Worker([queue], connection=conn)
    worker.work()
