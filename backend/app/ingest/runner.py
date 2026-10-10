"""
run_source — main ingest job function enqueued by the RQ worker.

Each call:
  1. Opens a DB session
  2. Loads the IngestSource
  3. Creates an IngestRun(status='running')
  4. Calls the appropriate adapter to fetch RawPostings
  5. For each RawPosting: dedup check → skip or insert
  6. Marks postings that disappeared from the source as closed
  7. Updates IngestSource.consecutive_failures and auto_paused
  8. Commits the IngestRun with final status
"""

import asyncio
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AsyncSessionLocal
from app.ingest.base import AdapterError, RawPosting
from app.ingest.dedup import duplicate_exists
from app.ingest.registry import adapter_for
from app.models.ingest_run import IngestRun
from app.models.ingest_source import IngestSource
from app.models.posting import Posting, WorkMode

_AUTO_PAUSE_THRESHOLD = 3


def run_source(source_id: str) -> None:
    """
    RQ job entry point (synchronous wrapper around the async implementation).
    RQ workers are sync by default; we create a new event loop per job.
    """
    asyncio.run(_run_source_async(UUID(source_id)))


async def _run_source_async(source_id: UUID) -> None:
    async with AsyncSessionLocal() as db:
        await _execute_run(db, source_id)


async def _execute_run(db: AsyncSession, source_id: UUID) -> None:
    source = await db.get(IngestSource, source_id)
    if source is None:
        return

    now = datetime.now(timezone.utc)
    run = IngestRun(
        source_id=source_id,
        started_at=now,
        status="running",
    )
    db.add(run)
    await db.flush()  # get run.id

    added = updated = closed = errors = 0
    error_log: list[str] = []
    status = "success"

    try:
        adapter = adapter_for(source)
        raw_postings = await adapter.fetch(source)
    except AdapterError as exc:
        error_log.append(str(exc))
        errors += 1
        status = "failed"
        raw_postings = []

    seen_refs: set[str] = set()

    for raw in raw_postings:
        try:
            is_dup = await duplicate_exists(db, raw.company, raw.title, raw.city)
            if is_dup:
                continue

            # Check by source_ref for update vs insert
            if raw.source_ref:
                seen_refs.add(raw.source_ref)
                stmt = select(Posting).where(
                    Posting.source_id == source_id,
                    Posting.source_ref == raw.source_ref,
                )
                existing = (await db.execute(stmt)).scalar_one_or_none()
                if existing:
                    # Update mutable fields
                    existing.closed_at = None  # re-open if it was closed
                    updated += 1
                    continue

            posting = _raw_to_posting(raw, source_id)
            db.add(posting)
            added += 1
        except Exception as exc:  # noqa: BLE001
            errors += 1
            error_log.append(f"Row error for {raw.title!r}: {exc}")
            if status == "success":
                status = "partial"

    # Close postings that disappeared from the source (source_ref not in current batch)
    if seen_refs and source_id:
        close_stmt = (
            select(Posting)
            .where(
                Posting.source_id == source_id,
                Posting.closed_at.is_(None),
                ~Posting.source_ref.in_(seen_refs),
                Posting.source_ref.isnot(None),
            )
        )
        stale = (await db.execute(close_stmt)).scalars().all()
        for p in stale:
            p.closed_at = datetime.now(timezone.utc)
            closed += 1

    # Update source stats
    if status == "failed":
        source.consecutive_failures += 1
        if source.consecutive_failures >= _AUTO_PAUSE_THRESHOLD:
            source.auto_paused = True
    else:
        source.consecutive_failures = 0
        source.last_run_at = datetime.now(timezone.utc)

    run.finished_at = datetime.now(timezone.utc)
    run.status = status
    run.added = added
    run.updated = updated
    run.closed = closed
    run.errors = errors
    run.error_log = error_log[:100]  # cap at 100 entries

    await db.commit()


def _raw_to_posting(raw: RawPosting, source_id: UUID) -> Posting:
    from datetime import date as date_type

    work_mode = WorkMode.onsite
    if raw.work_mode and raw.work_mode.lower() in WorkMode.__members__:
        work_mode = WorkMode(raw.work_mode.lower())

    return Posting(
        title=raw.title,
        company=raw.company,
        city=raw.city or "Unknown",
        province="ON",  # default; extraction will refine
        work_mode=work_mode,
        term=raw.term or "TBD",
        duration_months=4,  # default; extraction will refine
        deadline=raw.deadline or date_type.today(),
        description=raw.description or "",
        source_url=raw.source_url,
        skills=raw.skills,
        source_id=source_id,
        source_ref=raw.source_ref,
    )
