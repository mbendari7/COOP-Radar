"""
The logic for saved jobs.

All the database work happens here and the routers just call it.
A few choices worth knowing
  save_posting uses INSERT ON CONFLICT DO NOTHING so saving twice is safe
  list_saved joins the job in one query and loads events with selectin
  status_counts come from a GROUP BY over all their saved jobs and not just this page
  update_status logs an ApplicationEvent for every change
  export_csv builds a CSV of their whole tracker with pandas
"""

import io
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import String, case, cast, func, or_, select, text
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

# Stages where the deadline does not matter to the student anymore
_CLOSED_STATUSES = [
    ApplicationStatus.offer,
    ApplicationStatus.rejected,
    ApplicationStatus.withdrawn,
]


async def list_saved(
    db: AsyncSession,
    user_id: UUID,
    status_filter: ApplicationStatus | None,
    page: int,
    page_size: int,
) -> SavedPostingsPage:
    """
    A page of saved jobs for a person with the job data joined in.
    Events load with selectin so we avoid one query per row.
    Also sends this week's deadlines and the stats.
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

    # Status counts across every saved job and not just the filtered ones
    counts_stmt = (
        select(
            case(
                (SavedPosting.status.is_(None), "none"),
                # Cast the enum to text so both CASE branches are the same type
                else_=cast(SavedPosting.status, String),
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

    # Deadlines in the next 7 days across every saved job, not just this page.
    # deadline is a DATE column so compare it to dates. Jobs with no status (NULL)
    # have to be added on purpose because NULL NOT IN (...) is NULL and not TRUE
    today = date.today()
    week_end = today + timedelta(days=7)
    deadlines_stmt = (
        select(SavedPosting.id, Posting.id, Posting.title, Posting.company, Posting.deadline)
        .join(Posting, SavedPosting.posting_id == Posting.id)
        .where(
            SavedPosting.user_id == user_id,
            Posting.deadline >= today,
            Posting.deadline <= week_end,
            or_(
                SavedPosting.status.is_(None),
                SavedPosting.status.not_in(_CLOSED_STATUSES),
            ),
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
    Save a job for a person.

    Safe to repeat. If they already saved it we just give back the one
    that is there with no error.

    Gives back the saved job and whether it was new.
    Answers 404 if the job does not exist.
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
    """Unsave a job and its events go with it."""
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
    event_date: date | None = None,
) -> SavedPosting:
    """
    Change or clear the application status on a saved job.
    Logs an ApplicationEvent for every change.
    Answers 404 if it is not there or belongs to someone else.
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
    row.last_status_at = datetime.now(UTC)

    # Log the change in the history unless they are clearing the status
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
    event_date: date | None,
) -> SavedPosting:
    """
    Add a status event by hand, like noting an interview date after the fact.
    This also changes the current status on the saved job.
    """
    return await update_status(db, user_id, saved_posting_id, new_status, notes, event_date)


async def export_csv(
    db: AsyncSession,
    user_id: UUID,
) -> bytes:
    """
    Build a CSV of the person's whole tracker with pandas.
    Gives back raw bytes ready to download.
    """
    import pandas as pd  # imported here so pandas does not slow down other endpoints

    # Get every saved job with its job data
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
            "Deadline": p.deadline.isoformat() if p.deadline else "",
            "Status": row.status.value if row.status else "",
            "Saved At": row.saved_at.date().isoformat(),
            "Last Updated": row.last_status_at.date().isoformat() if row.last_status_at else "",
            "Posting URL": p.source_url or "",
        })

    df = pd.DataFrame(records)
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()
