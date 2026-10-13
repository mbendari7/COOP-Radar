"""
run_source imports one source. app/jobs.py starts it in the background.

Every run
  1. Opens a database session and loads the IngestSource
  2. Reuses the IngestRun made by Run now (run_id) or makes a new one
  3. Asks the source's adapter for RawPostings
  4. For each one
       same source and same source_ref updates the row we have and reopens it if closed
       almost the same as another job (company, city, close title) gets skipped
       anything else gets missing fields filled by extract_fields() and is added
  5. Marks this source's jobs that left the feed as closed
  6. Updates consecutive_failures and auto_paused on the source
  7. Commits the run, then queues embedding jobs for new jobs
"""

from datetime import UTC, date, datetime, timedelta
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
from app.services.education import fields_in_posting, grad_years_in_posting

_AUTO_PAUSE_THRESHOLD = 3
# Most career boards never give a deadline. Jobs without one get a guessed apply by date
# this far ahead. It is flagged in low_confidence_fields and pushed forward on every run
# while the job is still listed, and the job closes as soon as it leaves the board
_ESTIMATED_DEADLINE = timedelta(days=45)
_VALID_DURATIONS = {4, 8, 12, 16}


async def run_source(source_id: UUID, run_id: UUID | None = None) -> None:
    """Where the background job starts. Run one import then queue embeddings for new jobs."""
    from app.ingest.embed import enqueue_embed_job

    async with AsyncSessionLocal() as db:
        new_ids = await _execute_run(db, source_id, run_id)
    for posting_id in new_ids:
        enqueue_embed_job(posting_id)


async def _execute_run(
    db: AsyncSession, source_id: UUID, run_id: UUID | None = None
) -> list[UUID]:
    """Run one import pass and commit it. Gives back the ids of the new jobs."""
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
            # We already have this job from this source so update it and never duplicate.
            # This has to come before the fuzzy duplicate check or every run would
            # treat its own jobs as duplicates and then close them
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
            await db.flush()  # later rows need to see this one when checking duplicates
            new_postings.append(posting)
            added += 1
        except Exception as exc:  # noqa: BLE001 one bad row should not fail the whole run
            errors += 1
            error_log.append(f"Row error for {raw.title!r}: {exc}")
            if status == "success":
                status = "partial"

    # Close this source's jobs that left the feed. Skipped when the fetch failed
    # or came back empty so an outage never closes everything
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
    run.error_log = error_log[:100]  # keep at most 100 entries

    await db.commit()
    return [p.id for p in new_postings]


def _apply_updates(existing: Posting, raw: RawPosting) -> None:
    """Refresh the fields that can change and reopen the job if it was closed."""
    existing.closed_at = None
    if raw.title:
        existing.title = raw.title
    if raw.company:
        existing.company = raw.company
    if raw.description:
        existing.description = raw.description
    if raw.deadline:
        existing.deadline = raw.deadline
    elif "deadline" in (existing.low_confidence_fields or {}):
        # Still listed so keep the guessed apply by date ahead of today
        existing.deadline = max(existing.deadline, date.today() + _ESTIMATED_DEADLINE)
    if raw.source_url:
        existing.source_url = raw.source_url
    if raw.skills:
        existing.skills = raw.skills
    # Boards edit locations and our parsing gets better, so keep the location fresh
    if raw.city:
        existing.city = raw.city
    if raw.province is not None:
        existing.province = raw.province
    existing.country = raw.country
    _set_education(existing)


def _set_education(posting: Posting) -> None:
    """Programs and grad years the job asks for. Co-op matching uses these."""
    text = f"{posting.title}\n{posting.description or ''}"
    posting.fields_of_study = fields_in_posting(text)
    posting.grad_years = grad_years_in_posting(text)


async def _raw_to_posting(db: AsyncSession, raw: RawPosting, source_id: UUID) -> Posting:
    """
    Turn a RawPosting into a Posting and fill missing fields from the job text.
    Fields we had to guess go in low_confidence_fields so an admin can check them.
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

    posting = Posting(
        title=raw.title,
        company=raw.company,
        city=raw.city or "Unknown",
        # Career boards give a province when they can. RSS and JSON feeds rarely do
        province=raw.province if raw.province is not None else "ON",
        country=raw.country,
        work_mode=work_mode,
        term=term or "Open",
        duration_months=duration,
        deadline=raw.deadline or date.today() + _ESTIMATED_DEADLINE,
        description=raw.description or "",
        source_url=raw.source_url,
        skills=skills,
        source_id=source_id,
        source_ref=raw.source_ref,
        low_confidence_fields={k: v for k, v in low_confidence.items() if v < 1.0},
    )
    if raw.posted_at:
        posting.posted_at = raw.posted_at
    _set_education(posting)
    return posting
