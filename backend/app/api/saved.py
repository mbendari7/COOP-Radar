"""
Saved jobs. Every route needs you to be signed in.

GET    /api/saved               list with pages and an optional status filter
POST   /api/saved               save a job, safe to repeat
DELETE /api/saved/{id}          unsave it
PATCH  /api/saved/{id}/status   change the application status and log it
POST   /api/saved/{id}/events   add a dated note by hand
GET    /api/saved/export/csv    download the tracker as a CSV
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
    """Load a saved job together with its posting and events."""
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
    Download your whole tracker as a CSV file.
    Built on the server with pandas and sent straight to the browser.
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
    # The board loads up to 200 cards at once and the table loads 25
    page_size: int = Query(default=25, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SavedPostingsPage:
    """
    Your saved jobs plus status counts, deadlines and stats.
    You can filter by status. Newest saves come first.
    """
    return await svc.list_saved(db, current_user.id, status_filter, page, page_size)


@router.post("", response_model=SavedPostingOut)
async def save_posting(
    body: SaveIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SavedPostingOut:
    """
    Save a job. Safe to repeat. Answers 201 the first time and 200 after that.
    Answers 404 if the job does not exist.
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
    """Unsave a job. Answers 404 if it is not there or belongs to someone else."""
    await svc.unsave_posting(db, current_user.id, saved_posting_id)


@router.patch("/{saved_posting_id}/status", response_model=SavedPostingOut)
async def update_status(
    saved_posting_id: UUID,
    body: StatusUpdateIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SavedPostingOut:
    """
    Change the application status on a saved job and log the change.
    Send null to clear it. Answers 404 if it is not there or belongs to someone else.
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
    Add a status event by hand, like noting an interview date after the fact.
    This also changes the current status on the saved job.
    """
    await svc.add_event(
        db, current_user.id, saved_posting_id, body.status, body.notes, body.event_date
    )
    return await _load_full(saved_posting_id, db)
