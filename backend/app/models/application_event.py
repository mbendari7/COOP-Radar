"""
ApplicationEvent ORM model.

Each status change on a SavedPosting creates one row here, capturing the
new status, an optional free-text note, and an optional user-supplied date
(e.g. an interview date).  Cascades on DELETE from saved_postings.
"""

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import DATE, TIMESTAMP, Enum, ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
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
    # Optional note the student records for this status change
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Optional date the student associates with this event (e.g. interview date)
    event_date: Mapped[date | None] = mapped_column(DATE, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("NOW()"), nullable=False
    )

    saved_posting: Mapped["SavedPosting"] = relationship(back_populates="events")  # noqa: F821
