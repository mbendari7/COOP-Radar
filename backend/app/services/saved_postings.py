"""
Saved postings business logic.

All DB work happens here — routers are thin wrappers.
The key design decisions:

- save_posting uses INSERT … ON CONFLICT DO NOTHING (idempotent, FR-007)
- list_saved JOINs posting in one query to avoid N+1
- status_counts come from a single GROUP BY query on the same filtered set
"""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import case, func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.posting import Posting
from app.models.saved_posting import ApplicationStatus, SavedPosting
from app.schemas.posting import PostingListItem
from app.schemas.saved_posting import SavedPostingOut, SavedPostingsPage


async def list_saved(
    db: AsyncSession,
    user_id: UUID,
    status_filter: ApplicationStatus | None,
    page: int,
    page_size: int,
) -> SavedPostingsPage:
    """
    Return paginated saved postings for a user, joined with the posting data.
    Default order: most recently saved first.
    """
    base = (
        select(SavedPosting)
        .where(SavedPosting.user_id == user_id)
        .join(Posting, SavedPosting.posting_id == Posting.id)
    )

    if status_filter is not None:
        base = base.where(SavedPosting.status == status_filter)

    # Total count before pagination
    count_stmt = select(func.count()).select_from(base.subquery())
    total: int = (await db.execute(count_stmt)).scalar_one()

    # Paginated rows with posting eagerly loaded
    from sqlalchemy.orm import selectinload
    stmt = (
        base
        .options(selectinload(SavedPosting.posting))
        .order_by(SavedPosting.saved_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await db.execute(stmt)).scalars().all()

    # Status counts across ALL saved postings (not just the current page/filter)
    counts_stmt = (
        select(
            case(
                (SavedPosting.status == None, "none"),  # noqa: E711
                else_=SavedPosting.status,
            ).label("s"),
            func.count().label("n"),
        )
        .where(SavedPosting.user_id == user_id)
        .group_by(text("s"))
    )
    counts_rows = (await db.execute(counts_stmt)).all()
    status_counts: dict[str, int] = {
        "applied": 0, "interviewing": 0, "offer": 0, "rejected": 0, "none": 0
    }
    for s, n in counts_rows:
        status_counts[str(s)] = n

    items = [
        SavedPostingOut(
            id=row.id,
            saved_at=row.saved_at,
            status=row.status,
            posting=PostingListItem.model_validate(row.posting),
        )
        for row in rows
    ]

    return SavedPostingsPage(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        status_counts=status_counts,
    )


async def save_posting(
    db: AsyncSession,
    user_id: UUID,
    posting_id: UUID,
) -> tuple[SavedPosting, bool]:
    """
    Bookmark a posting for a user.

    Idempotent — if the (user_id, posting_id) pair already exists, returns
    the existing record without error (FR-007).

    Returns (saved_posting, created: bool).
    Raises 404 if the posting_id doesn't exist.
    """
    # Verify posting exists first
    posting = (
        await db.execute(select(Posting).where(Posting.id == posting_id))
    ).scalar_one_or_none()

    if posting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "Posting not found", "code": "POSTING_NOT_FOUND"},
        )

    # ON CONFLICT DO NOTHING — safe concurrent upsert
    stmt = (
        pg_insert(SavedPosting)
        .values(user_id=user_id, posting_id=posting_id)
        .on_conflict_do_nothing(constraint="ux_saved_postings_user_posting")
        .returning(SavedPosting.id)
    )
    result = (await db.execute(stmt)).scalar_one_or_none()

    if result is not None:
        # Freshly inserted — fetch the full row
        new_row = (
            await db.execute(select(SavedPosting).where(SavedPosting.id == result))
        ).scalar_one()
        await db.commit()
        return new_row, True
    else:
        # Already existed — return existing record
        existing = (
            await db.execute(
                select(SavedPosting).where(
                    SavedPosting.user_id == user_id,
                    SavedPosting.posting_id == posting_id,
                )
            )
        ).scalar_one()
        return existing, False


async def unsave_posting(
    db: AsyncSession,
    user_id: UUID,
    saved_posting_id: UUID,
) -> None:
    """
    Remove a saved posting.
    Raises 404 if it doesn't exist or belongs to a different user.
    """
    row = (
        await db.execute(
            select(SavedPosting).where(
                SavedPosting.id == saved_posting_id,
                SavedPosting.user_id == user_id,
            )
        )
    ).scalar_one_or_none()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "Saved posting not found", "code": "SAVED_NOT_FOUND"},
        )

    await db.delete(row)
    await db.commit()


async def update_status(
    db: AsyncSession,
    user_id: UUID,
    saved_posting_id: UUID,
    new_status: ApplicationStatus | None,
) -> SavedPosting:
    """
    Update (or clear) the application status on a saved posting.
    Raises 404 if not found or owned by another user.
    """
    row = (
        await db.execute(
            select(SavedPosting).where(
                SavedPosting.id == saved_posting_id,
                SavedPosting.user_id == user_id,
            )
        )
    ).scalar_one_or_none()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "Saved posting not found", "code": "SAVED_NOT_FOUND"},
        )

    row.status = new_status
    await db.commit()
    await db.refresh(row)
    return row
