"""
Saved postings router — all endpoints require authentication.

GET  /api/saved               — list with pagination + optional status filter
POST /api/saved               — save a posting (idempotent)
DELETE /api/saved/{id}        — unsave
PATCH  /api/saved/{id}/status — update application status (creates event)
POST   /api/saved/{id}/events — manually add an event with notes
GET    /api/saved/export/csv  — download tracker as CSV
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import get_current_user
from app.models.saved_posting import ApplicationStatus
from app.models.user import User
from app.schemas.saved_posting import (
    EventCreateIn,
    SavedPostingOut,
    SavedPostingsPage,
    SaveIn,
    StatusUpdateIn,
)
from app.services import saved_postings as svc

router = APIRouter(prefix="/saved", tags=["saved"])


async def _load_full(saved_id: UUID, db: AsyncSession) -> SavedPostingOut:
    """Fetch a SavedPosting with its posting + events eagerly loaded."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.models.saved_posting import SavedPosting
    from app.schemas.posting import PostingListItem
    from app.schemas.saved_posting import ApplicationEventOut

    row = (
        await db.execute(
            select(SavedPosting)
            .where(SavedPosting.id == saved_id)
            .options(
                selectinload(SavedPosting.posting),
                selectinload(SavedPosting.events),
            )
        )
    ).scalar_one()

    return SavedPostingOut(
        id=row.id,
        saved_at=row.saved_at,
        last_status_at=row.last_status_at,
        status=row.status,
        posting=PostingListItem.model_validate(row.posting),
        events=[ApplicationEventOut.model_validate(e) for e in row.events],
    )


@router.get("/export/csv")
async def export_csv(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """
    Download the current user's full tracker as a CSV file.
    Generated server-side with pandas; streamed directly to the browser.
    """
    import io
    csv_bytes = await svc.export_csv(db, current_user.id)

    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=coopradar-tracker.csv"},
    )


@router.get("", response_model=SavedPostingsPage)
async def list_saved(
    status_filter: ApplicationStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    # The board view loads up to 200 cards at once; the table uses 25
    page_size: int = Query(default=25, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SavedPostingsPage:
    """
    Return the current user's saved postings with status counts, deadlines, and stats.
    Optionally filter by status.  Ordered by most recently saved.
    """
    return await svc.list_saved(db, current_user.id, status_filter, page, page_size)


@router.post("", response_model=SavedPostingOut)
async def save_posting(
    body: SaveIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SavedPostingOut:
    """
    Bookmark a posting.  Idempotent — returns 201 on first save, 200 if already saved.
    Returns 404 if the posting_id doesn't exist.
    """
    from fastapi.responses import JSONResponse

    saved, created = await svc.save_posting(db, current_user.id, body.posting_id)
    out = await _load_full(saved.id, db)
    status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return JSONResponse(content=out.model_dump(mode="json"), status_code=status_code)  # type: ignore[return-value]


@router.delete("/{saved_posting_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unsave_posting(
    saved_posting_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Remove a saved posting. Returns 404 if not found or owned by another user."""
    await svc.unsave_posting(db, current_user.id, saved_posting_id)


@router.patch("/{saved_posting_id}/status", response_model=SavedPostingOut)
async def update_status(
    saved_posting_id: UUID,
    body: StatusUpdateIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SavedPostingOut:
    """
    Update the application status on a saved posting and record the change as an event.
    Pass null status to clear. Returns 404 if not found or owned by another user.
    """
    await svc.update_status(
        db, current_user.id, saved_posting_id, body.status, body.notes, body.event_date
    )
    return await _load_full(saved_posting_id, db)


@router.post(
    "/{saved_posting_id}/events",
    response_model=SavedPostingOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_event(
    saved_posting_id: UUID,
    body: EventCreateIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SavedPostingOut:
    """
    Manually add a status event (e.g. note an interview date retroactively).
    Also updates the current status on the saved posting.
    """
    await svc.add_event(
        db, current_user.id, saved_posting_id, body.status, body.notes, body.event_date
    )
    return await _load_full(saved_posting_id, db)
