"""Admin only routes for managing where jobs get imported from."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import get_admin_user
from app.models.user import User
from app.schemas.ingest import IngestSourceOut, RunsPage, SourcePatchIn, TriggerRunOut
from app.services.ingest import list_runs, list_sources, patch_source, trigger_run

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/sources", response_model=list[IngestSourceOut])
async def get_sources(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_admin_user),
) -> list[IngestSourceOut]:
    """List every source with how its last run went."""
    return await list_sources(db)


@router.get("/sources/{source_id}/runs", response_model=RunsPage)
async def get_source_runs(
    source_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_admin_user),
) -> RunsPage:
    """Run history for one source, a page at a time."""
    return await list_runs(db, source_id, page, page_size)


@router.post("/sources/{source_id}/run", response_model=TriggerRunOut, status_code=202)
async def trigger_source_run(
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_admin_user),
) -> TriggerRunOut:
    """Run a source right now. Answers 409 if it is already running."""
    return await trigger_run(db, source_id)


@router.patch("/sources/{source_id}", response_model=IngestSourceOut)
async def patch_source_endpoint(
    source_id: UUID,
    data: SourcePatchIn,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_admin_user),
) -> IngestSourceOut:
    """Turn a source on or off, or unpause it."""
    return await patch_source(db, source_id, data)
