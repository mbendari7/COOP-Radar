"""
Saved postings business logic.

All DB work happens here — routers are thin wrappers.
Design decisions:
- save_posting uses INSERT … ON CONFLICT DO NOTHING (idempotent, FR-007)
- list_saved JOINs posting in one query; events are loaded via selectin
- status_counts come from a GROUP BY on all user's saved postings (not the current page)
- update_status auto-creates an ApplicationEvent for every change
- export_csv streams a CSV built with pandas for the user's full tracker data
"""

import io
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import case, func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application_event import ApplicationEvent
from app.models.posting import Posting
from app.models.saved_posting import ApplicationStatus, SavedPosting
from app.schemas.posting import PostingListItem
from app.schemas.saved_posting import (
    ApplicationEventOut,
    SavedPostingOut,
    SavedPostingsPage,
)


async def list_saved(
    db: AsyncSession,
    user_id: UUID,
    status_filter: ApplicationStatus | None,
    page: int,
    page_size: int,
) -> SavedPostingsPage:
    """
    Return paginated saved postings for a user, joined with the posting data.
    Events are loaded via selectin (avoids N+1).
    Includes deadlines this week and stats in the response.
    """
    from sqlalchemy.orm import selectinload

    base = (
        select(SavedPosting)
        .where(SavedPosting.user_id == user_id)
        .join(Posting, SavedPosting.posting_id == Posting.id)
    )

    if status_filter is not None:
        base = base.where(SavedPosting.status == status_filter)

    count_stmt = select(func.count()).select_from(base.subquery())
    total: int = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        base
        .options(
            selectinload(SavedPosting.posting),
            selectinload(SavedPosting.events),
        )
        .order_by(SavedPosting.saved_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await db.execute(stmt)).scalars().all()

    # Status counts across ALL saved postings (not filtered subset)
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
        "saved": 0, "applying": 0, "applied": 0,
        "interview": 0, "offer": 0, "rejected": 0, "withdrawn": 0, "none": 0,
    }
    for s, n in counts_rows:
        status_counts[str(s)] = n

    # Deadlines within the next 7 days (all saved postings, not just current page)
    now = datetime.now(timezone.utc)
    week_end = now + timedelta(days=7)
    deadlines_stmt = (
        select(SavedPosting.id, Posting.id, Posting.title, Posting.company, Posting.deadline)
        .join(Posting, SavedPosting.posting_id == Posting.id)
        .where(
            SavedPosting.user_id == user_id,
            Posting.deadline >= now,
            Posting.deadline <= week_end,
            SavedPosting.status.not_in([ApplicationStatus.offer, ApplicationStatus.rejected, ApplicationStatus.withdrawn]),
        )
        .order_by(Posting.deadline.asc())
    )
    deadline_rows = (await db.execute(deadlines_stmt)).all()
    deadlines_this_week = [
        {
            "saved_id": str(r[0]),
            "posting_id": str(r[1]),
            "title": r[2],
            "company": r[3],
            "deadline": r[4].isoformat() if r[4] else "",
        }
        for r in deadline_rows
    ]

    items = [
        SavedPostingOut(
            id=row.id,
            saved_at=row.saved_at,
            last_status_at=row.last_status_at,
            status=row.status,
            posting=PostingListItem.model_validate(row.posting),
            events=[ApplicationEventOut.model_validate(e) for e in row.events],
        )
        for row in rows
    ]

    return SavedPostingsPage(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        status_counts=status_counts,
        total_applied=status_counts.get("applied", 0),
        total_interview=status_counts.get("interview", 0),
        total_offer=status_counts.get("offer", 0),
        deadlines_this_week=deadlines_this_week,
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
    posting = (
        await db.execute(select(Posting).where(Posting.id == posting_id))
    ).scalar_one_or_none()

    if posting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "Posting not found", "code": "POSTING_NOT_FOUND"},
        )

    stmt = (
        pg_insert(SavedPosting)
        .values(user_id=user_id, posting_id=posting_id)
        .on_conflict_do_nothing(constraint="ux_saved_postings_user_posting")
        .returning(SavedPosting.id)
    )
    result = (await db.execute(stmt)).scalar_one_or_none()

    if result is not None:
        new_row = (
            await db.execute(select(SavedPosting).where(SavedPosting.id == result))
        ).scalar_one()
        await db.commit()
        return new_row, True
    else:
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
    """Remove a saved posting (and all its events via CASCADE)."""
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
    notes: str | None = None,
    event_date: "date | None" = None,  # type: ignore[name-defined]
) -> SavedPosting:
    """
    Update (or clear) the application status on a saved posting.
    Automatically creates an ApplicationEvent for every status change.
    Raises 404 if not found or owned by another user.
    """
    from datetime import date  # noqa: F811

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
    row.last_status_at = datetime.now(timezone.utc)

    # Record the status change in the event history (skip if clearing status)
    if new_status is not None:
        event = ApplicationEvent(
            saved_posting_id=row.id,
            status=new_status,
            notes=notes,
            event_date=event_date,
        )
        db.add(event)

    await db.commit()
    await db.refresh(row)
    return row


async def add_event(
    db: AsyncSession,
    user_id: UUID,
    saved_posting_id: UUID,
    new_status: ApplicationStatus,
    notes: str | None,
    event_date: "date | None",  # type: ignore[name-defined]
) -> SavedPosting:
    """
    Manually add a status event (e.g. note an interview date retroactively).
    Also updates the current status on the SavedPosting.
    """
    return await update_status(db, user_id, saved_posting_id, new_status, notes, event_date)


async def export_csv(
    db: AsyncSession,
    user_id: UUID,
) -> bytes:
    """
    Build a CSV file of the user's full tracker data using pandas.
    Returns raw bytes ready to be streamed as a file download.
    """
    import pandas as pd  # local import — pandas is optional dep for this path

    # Fetch all saved postings with their posting data
    from sqlalchemy.orm import selectinload

    stmt = (
        select(SavedPosting)
        .where(SavedPosting.user_id == user_id)
        .options(selectinload(SavedPosting.posting))
        .order_by(SavedPosting.saved_at.desc())
    )
    rows = (await db.execute(stmt)).scalars().all()

    records = []
    for row in rows:
        p = row.posting
        records.append({
            "Title": p.title,
            "Company": p.company,
            "City": p.city,
            "Province": p.province,
            "Work Mode": p.work_mode.value if p.work_mode else "",
            "Term": p.term,
            "Duration (months)": p.duration_months,
            "Deadline": p.deadline.date().isoformat() if p.deadline else "",
            "Status": row.status.value if row.status else "",
            "Saved At": row.saved_at.date().isoformat(),
            "Last Updated": row.last_status_at.date().isoformat() if row.last_status_at else "",
            "Posting URL": p.source_url or "",
        })

    df = pd.DataFrame(records)
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()
