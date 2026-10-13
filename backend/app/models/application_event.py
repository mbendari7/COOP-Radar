"""
One row for every status change on a saved job.

It keeps the new status, an optional note and an optional date the student
picks, like an interview date. Rows go away when the saved job is deleted.
"""

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DATE, TIMESTAMP, Enum, ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.saved_posting import SavedPosting
from app.models.saved_posting import ApplicationStatus


class ApplicationEvent(Base):
    __tablename__ = "application_events"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    saved_posting_id: Mapped[UUID] = mapped_column(
        ForeignKey("saved_postings.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, name="application_status_enum"), nullable=False
    )
    # A note the student can add for this change
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # A date the student can tie to this event, like the interview day
    event_date: Mapped[date | None] = mapped_column(DATE, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("NOW()"), nullable=False
    )

    saved_posting: Mapped["SavedPosting"] = relationship(back_populates="events")

    __table_args__ = (
        Index("idx_application_events_saved_posting_id", "saved_posting_id"),
        Index("idx_application_events_created_at", text("created_at DESC")),
    )
