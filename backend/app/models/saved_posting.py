"""
SavedPosting ORM model and ApplicationStatus enum.

One row per (user, posting) bookmark.  The UNIQUE constraint on
(user_id, posting_id) enforces "one save per pair" at the database level,
making the save operation safely idempotent via ON CONFLICT DO NOTHING.

Both FKs use ON DELETE CASCADE so:
- Deleting a user removes all their saved postings (FR-013)
- Deleting a posting removes it from all saved lists
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
    Seven stages of a co-op application lifecycle.
    str mixin lets FastAPI serialise these as plain strings automatically.
    NULL in the database means "no status set" — distinct from any value here.
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
    # NULL = no status set; not the same as any of the four enum values
    status: Mapped[ApplicationStatus | None] = mapped_column(
        Enum(ApplicationStatus, name="application_status_enum"), nullable=True
    )
    saved_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("NOW()"), nullable=False
    )
    # Updated whenever status changes — used for "last updated" sort on tracker table
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
        # Redundant with the unique constraint above, but migration 0002 created it;
        # declaring it keeps autogenerate from proposing to drop it.
        Index("ux_saved_postings_user_posting_idx", "user_id", "posting_id", unique=True),
    )
