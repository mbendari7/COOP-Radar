"""
run_source — main ingest job function enqueued by the RQ worker.

Each call:
  1. Opens a DB session and loads the IngestSource
  2. Reuses the IngestRun created by "Run now" (run_id) or creates a new one
  3. Calls the source's adapter to fetch RawPostings
  4. For each RawPosting:
       - same source + same source_ref  -> update the existing row (re-open if closed)
       - near-duplicate of another posting (company + city + ~title) -> skip
       - otherwise -> fill missing fields via extract_fields() and insert
  5. Marks this source's postings that disappeared from the feed as closed
  6. Updates consecutive_failures / auto_paused on the source
  7. Commits the run, then queues embedding jobs for new postings
"""

import asyncio
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AsyncSessionLocal
from app.ingest.base import AdapterError, RawPosting
from app.ingest.dedup import duplicate_exists
from app.ingest.extract import extract_fields
from app.ingest.registry import adapter_for
from app.models.ingest_run import IngestRun
from app.models.ingest_source import IngestSource
from app.models.posting import Posting, WorkMode

_AUTO_PAUSE_THRESHOLD = 3
_VALID_DURATIONS = {4, 8, 12, 16}


def run_source(source_id: str, run_id: str | None = None) -> None:
    """
    RQ job entry point (synchronous wrapper around the async implementation).
    RQ workers are sync by default; we create a new event loop per job.
    """
    asyncio.run(_run_source_async(UUID(source_id), UUID(run_id) if run_id else None))


async def _run_source_async(source_id: UUID, run_id: UUID | None) -> None:
    from app.ingest.embed import enqueue_embed_job

    async with AsyncSessionLocal() as db:
        new_ids = await _execute_run(db, source_id, run_id)
    for posting_id in new_ids:
        enqueue_embed_job(posting_id)


async def _execute_run(
    db: AsyncSession, source_id: UUID, run_id: UUID | None = None
) -> list[UUID]:
    """Run one ingestion pass and commit it. Returns the IDs of newly inserted postings."""
    source = await db.get(IngestSource, source_id)
    if source is None:
        return []

    run = await db.get(IngestRun, run_id) if run_id else None
    if run is None:
        run = IngestRun(source_id=source_id, started_at=datetime.now(UTC), status="running")
        db.add(run)
        await db.flush()

    added = updated = closed = errors = 0
    error_log: list[str] = []
    status = "success"
    new_postings: list[Posting] = []

    raw_postings: list[RawPosting] = []
    try:
        raw_postings = await adapter_for(source).fetch(source)
    except (AdapterError, ValueError) as exc:
        error_log.append(str(exc))
        errors += 1
        status = "failed"

    seen_refs: set[str] = set()

    for raw in raw_postings:
        try:
            # Same posting seen before from this source -> update, never duplicate.
            # This check must come before the fuzzy dedup check, otherwise every
            # re-run would treat its own postings as duplicates and then close them.
            if raw.source_ref:
                seen_refs.add(raw.source_ref)
                existing = (
                    await db.execute(
                        select(Posting).where(
                            Posting.source_id == source_id,
                            Posting.source_ref == raw.source_ref,
                        )
                    )
                ).scalar_one_or_none()
                if existing is not None:
                    _apply_updates(existing, raw)
                    updated += 1
                    continue

            if await duplicate_exists(db, raw.company, raw.title, raw.city):
                continue

            posting = await _raw_to_posting(db, raw, source_id)
            db.add(posting)
            await db.flush()  # later rows' duplicate checks must see this one
            new_postings.append(posting)
            added += 1
        except Exception as exc:  # noqa: BLE001 — one bad row must not fail the run
            errors += 1
            error_log.append(f"Row error for {raw.title!r}: {exc}")
            if status == "success":
                status = "partial"

    # Close this source's postings that disappeared from the feed. Skipped when the
    # fetch failed or returned nothing, so an outage never closes everything.
    if seen_refs:
        stale = (
            await db.execute(
                select(Posting).where(
                    Posting.source_id == source_id,
                    Posting.closed_at.is_(None),
                    Posting.source_ref.is_not(None),
                    Posting.source_ref.not_in(seen_refs),
                )
            )
        ).scalars().all()
        now = datetime.now(UTC)
        for p in stale:
            p.closed_at = now
            closed += 1

    if status == "failed":
        source.consecutive_failures += 1
        if source.consecutive_failures >= _AUTO_PAUSE_THRESHOLD:
            source.auto_paused = True
    else:
        source.consecutive_failures = 0
        source.last_run_at = datetime.now(UTC)

    run.finished_at = datetime.now(UTC)
    run.status = status
    run.added = added
    run.updated = updated
    run.closed = closed
    run.errors = errors
    run.error_log = error_log[:100]  # cap at 100 entries

    await db.commit()
    return [p.id for p in new_postings]


def _apply_updates(existing: Posting, raw: RawPosting) -> None:
    """Refresh mutable fields from the feed and re-open the posting if it was closed."""
    existing.closed_at = None
    if raw.title:
        existing.title = raw.title
    if raw.description:
        existing.description = raw.description
    if raw.deadline:
        existing.deadline = raw.deadline
    if raw.source_url:
        existing.source_url = raw.source_url
    if raw.skills:
        existing.skills = raw.skills


async def _raw_to_posting(db: AsyncSession, raw: RawPosting, source_id: UUID) -> Posting:
    """
    Convert a RawPosting into a Posting, filling missing fields from the posting text.
    Fields we had to guess are recorded in low_confidence_fields for admin review.
    """
    work_mode_str = (raw.work_mode or "").lower() or None
    term = raw.term or None
    skills = list(raw.skills)
    duration = 4
    low_confidence: dict[str, float] = {}

    if not (work_mode_str and term and skills):
        extracted = await extract_fields(db, f"{raw.title}\n{raw.description or ''}")
        if not work_mode_str and extracted.work_mode:
            work_mode_str = extracted.work_mode
            low_confidence["work_mode"] = extracted.confidence_map.get("work_mode", 0.0)
        if not term and extracted.term:
            term = extracted.term
            low_confidence["term"] = extracted.confidence_map.get("term", 0.0)
        if not skills and extracted.skills:
            skills = extracted.skills
            low_confidence["skills"] = extracted.confidence_map.get("skills", 0.0)
        if extracted.duration_months in _VALID_DURATIONS:
            duration = extracted.duration_months

    work_mode = WorkMode.onsite
    if work_mode_str and work_mode_str in WorkMode.__members__:
        work_mode = WorkMode(work_mode_str)
    if not raw.city:
        low_confidence["city"] = 0.0
    if not raw.deadline:
        low_confidence["deadline"] = 0.0

    return Posting(
        title=raw.title,
        company=raw.company,
        city=raw.city or "Unknown",
        province="ON",  # feeds rarely include a province; admins can correct it
        work_mode=work_mode,
        term=term or "TBD",
        duration_months=duration,
        deadline=raw.deadline or date.today(),
        description=raw.description or "",
        source_url=raw.source_url,
        skills=skills,
        source_id=source_id,
        source_ref=raw.source_ref,
        low_confidence_fields={k: v for k, v in low_confidence.items() if v < 1.0},
    )
