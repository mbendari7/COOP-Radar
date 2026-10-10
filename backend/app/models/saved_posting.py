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
from uuid import UUID, uuid4

from sqlalchemy import TIMESTAMP, Enum, ForeignKey, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class ApplicationStatus(str, enum.Enum):
    """
    The four valid application tracking states.
    str mixin lets FastAPI serialise these as plain strings automatically.
    NULL in the database means "no status set" — distinct from any value here.
    """
    applied      = "applied"
    interviewing = "interviewing"
    offer        = "offer"
    rejected     = "rejected"


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

    user: Mapped["User"] = relationship(back_populates="saved_postings")  # noqa: F821
    posting: Mapped["Posting"] = relationship()  # noqa: F821

    __table_args__ = (
        UniqueConstraint("user_id", "posting_id", name="ux_saved_postings_user_posting"),
    )
