"""
Saved postings router — all endpoints require authentication.

GET  /api/saved               — list with pagination + optional status filter
POST /api/saved               — save a posting (idempotent)
DELETE /api/saved/{id}        — unsave
PATCH  /api/saved/{id}/status — update application status
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import get_current_user
from app.models.saved_posting import ApplicationStatus
from app.models.user import User
from app.schemas.saved_posting import (
    SavedPostingOut,
    SavedPostingsPage,
    SaveIn,
    StatusUpdateIn,
)
from app.services import saved_postings as svc

router = APIRouter(prefix="/saved", tags=["saved"])


@router.get("", response_model=SavedPostingsPage)
async def list_saved(
    status_filter: ApplicationStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SavedPostingsPage:
    """
    Return the current user's saved postings.
    Optionally filter by status (applied/interviewing/offer/rejected).
    Ordered by most recently saved.
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
    from fastapi import Response
    from fastapi.responses import JSONResponse

    saved, created = await svc.save_posting(db, current_user.id, body.posting_id)

    # We need to load the posting relationship for the response
    from sqlalchemy.orm import selectinload
    from sqlalchemy import select
    from app.models.saved_posting import SavedPosting

    row = (
        await db.execute(
            select(SavedPosting)
            .where(SavedPosting.id == saved.id)
            .options(selectinload(SavedPosting.posting))
        )
    ).scalar_one()

    from app.schemas.posting import PostingListItem
    out = SavedPostingOut(
        id=row.id,
        saved_at=row.saved_at,
        status=row.status,
        posting=PostingListItem.model_validate(row.posting),
    )
    status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return JSONResponse(content=out.model_dump(mode="json"), status_code=status_code)


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
    Update the application status on a saved posting.
    Pass null to clear the status.  Returns 404 if not found or owned by another user.
    """
    from sqlalchemy.orm import selectinload
    from sqlalchemy import select
    from app.models.saved_posting import SavedPosting

    updated = await svc.update_status(db, current_user.id, saved_posting_id, body.status)

    row = (
        await db.execute(
            select(SavedPosting)
            .where(SavedPosting.id == updated.id)
            .options(selectinload(SavedPosting.posting))
        )
    ).scalar_one()

    from app.schemas.posting import PostingListItem
    return SavedPostingOut(
        id=row.id,
        saved_at=row.saved_at,
        status=row.status,
        posting=PostingListItem.model_validate(row.posting),
    )
