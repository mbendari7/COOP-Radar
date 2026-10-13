"""
Saved jobs and the application status list.

One row for each person and job they saved. The database only allows one row
per pair, so saving twice is safe and does nothing the second time.

Both links cascade on delete, so
deleting a person removes everything they saved
deleting a job removes it from every saved list
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import TIMESTAMP, Enum, ForeignKey, Index, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.application_event import ApplicationEvent
    from app.models.posting import Posting
    from app.models.user import User

from app.db import Base


class ApplicationStatus(enum.StrEnum):
    """
    The stages a co-op application goes through.
    The str mixin lets FastAPI send these as plain strings.
    NULL in the database means no status yet, which is not the same as any value here.
    """
    saved      = "saved"
    applying   = "applying"
    applied    = "applied"
    interview  = "interview"
    offer      = "offer"
    rejected   = "rejected"
    withdrawn  = "withdrawn"


class SavedPosting(Base):
    __tablename__ = "saved_postings"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    posting_id: Mapped[UUID] = mapped_column(
        ForeignKey("postings.id", ondelete="CASCADE"), nullable=False
    )
    # NULL means no status yet and is not the same as any status value
    status: Mapped[ApplicationStatus | None] = mapped_column(
        Enum(ApplicationStatus, name="application_status_enum"), nullable=True
    )
    saved_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("NOW()"), nullable=False
    )
    # Changes whenever the status does. The tracker sorts by it for last updated
    last_status_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    user: Mapped["User"] = relationship(back_populates="saved_postings")
    posting: Mapped["Posting"] = relationship()
    events: Mapped[list["ApplicationEvent"]] = relationship(
        back_populates="saved_posting",
        order_by="ApplicationEvent.created_at.desc()",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("user_id", "posting_id", name="ux_saved_postings_user_posting"),
        Index("idx_saved_postings_user_id", "user_id"),
        Index("idx_saved_postings_posting_id", "posting_id"),
        Index("idx_saved_postings_status", "status"),
        Index("idx_saved_postings_saved_at", text("saved_at DESC")),
        # Doubles up on the unique constraint above but migration 0002 made it
        # and listing it here stops autogenerate from trying to drop it
        Index("ux_saved_postings_user_posting_idx", "user_id", "posting_id", unique=True),
    )
