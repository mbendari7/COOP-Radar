"""Service layer for admin ingest source management."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ingest_run import IngestRun
from app.models.ingest_source import IngestSource
from app.schemas.ingest import IngestRunOut, IngestSourceOut, RunsPage, SourcePatchIn, TriggerRunOut


async def list_sources(db: AsyncSession) -> list[IngestSourceOut]:
    """List all ingest sources with their latest run stats."""
    # Subquery: most recent run per source
    latest_run_sq = (
        select(
            IngestRun.source_id,
            func.max(IngestRun.started_at).label("max_started"),
        )
        .group_by(IngestRun.source_id)
        .subquery()
    )

    stmt = (
        select(IngestSource, IngestRun)
        .outerjoin(
            latest_run_sq,
            IngestSource.id == latest_run_sq.c.source_id,
        )
        .outerjoin(
            IngestRun,
            (IngestRun.source_id == latest_run_sq.c.source_id)
            & (IngestRun.started_at == latest_run_sq.c.max_started),
        )
        .order_by(IngestSource.created_at)
    )

    rows = (await db.execute(stmt)).all()

    result = []
    for source, run in rows:
        result.append(
            IngestSourceOut(
                id=source.id,
                name=source.name,
                adapter_type=source.adapter_type,
                enabled=source.enabled,
                auto_paused=source.auto_paused,
                last_run_at=run.started_at if run else None,
                last_run_status=run.status if run else None,
                last_run_added=run.added if run else None,
                last_run_updated=run.updated if run else None,
                last_run_closed=run.closed if run else None,
                last_run_errors=run.errors if run else None,
            )
        )
    return result


async def list_runs(
    db: AsyncSession,
    source_id: UUID,
    page: int = 1,
    page_size: int = 20,
) -> RunsPage:
    """Return paginated run history for a source."""
    source = await db.get(IngestSource, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail={"detail": "Source not found", "code": "NOT_FOUND"})

    count_stmt = select(func.count()).where(IngestRun.source_id == source_id)
    total: int = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        select(IngestRun)
        .where(IngestRun.source_id == source_id)
        .order_by(IngestRun.started_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    runs = (await db.execute(stmt)).scalars().all()

    items = [
        IngestRunOut(
            id=run.id,
            started_at=run.started_at,
            finished_at=run.finished_at,
            status=run.status,
            added=run.added,
            updated=run.updated,
            closed=run.closed,
            errors=run.errors,
            error_log=run.error_log or [],
        )
        for run in runs
    ]
    return RunsPage(items=items, total=total, page=page, page_size=page_size)


async def trigger_run(db: AsyncSession, redis: object, source_id: UUID) -> TriggerRunOut:
    """
    Trigger an immediate ingestion run for the given source.
    Returns 409 if a run is already in progress.
    Returns 422 if the source is auto-paused.
    """
    source = await db.get(IngestSource, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail={"detail": "Source not found", "code": "NOT_FOUND"})

    if source.auto_paused:
        raise HTTPException(
            status_code=422,
            detail={"detail": "Source is auto-paused. Re-enable it first.", "code": "SOURCE_PAUSED"},
        )

    # Check if already running
    running_stmt = select(IngestRun).where(
        IngestRun.source_id == source_id,
        IngestRun.status == "running",
    )
    existing = (await db.execute(running_stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=409,
            detail={"detail": "A run is already in progress.", "code": "ALREADY_RUNNING"},
        )

    # Create a run record to track it
    run = IngestRun(
        source_id=source_id,
        started_at=datetime.now(timezone.utc),
        status="running",
    )
    db.add(run)
    await db.flush()

    # Enqueue to RQ (best effort — fails gracefully if Redis is unavailable)
    try:
        from app.worker import create_queue
        import redis as _redis
        conn = _redis.from_url(__import__("os").getenv("REDIS_URL", "redis://localhost:6379/0"))
        queue = create_queue(conn)
        queue.enqueue("app.ingest.runner.run_source", str(source_id))
    except Exception:
        pass  # Run record created; worker will pick it up via scheduler

    await db.commit()
    return TriggerRunOut(run_id=run.id, message="Run queued.")


async def patch_source(
    db: AsyncSession,
    source_id: UUID,
    data: SourcePatchIn,
) -> IngestSourceOut:
    """Enable, disable, or un-pause a source."""
    source = await db.get(IngestSource, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail={"detail": "Source not found", "code": "NOT_FOUND"})

    if data.enabled is not None:
        source.enabled = data.enabled
    if data.auto_paused is not None:
        source.auto_paused = data.auto_paused
        if not data.auto_paused:
            source.consecutive_failures = 0  # reset on re-enable

    await db.commit()
    await db.refresh(source)

    return IngestSourceOut(
        id=source.id,
        name=source.name,
        adapter_type=source.adapter_type,
        enabled=source.enabled,
        auto_paused=source.auto_paused,
        last_run_at=source.last_run_at,
        last_run_status=None,
        last_run_added=None,
        last_run_updated=None,
        last_run_closed=None,
        last_run_errors=None,
    )
