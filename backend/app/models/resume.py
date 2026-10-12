from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import TIMESTAMP, CheckConstraint, ForeignKey, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.match_result import MatchResult


class Resume(Base):
    """
    Stores resume metadata and extracted text for one user.
    Only one resume per user is kept at a time (UNIQUE on user_id).
    The raw file is never persisted; only extracted_text is stored.
    """

    __tablename__ = "resumes"
    __table_args__ = (
        CheckConstraint("file_size > 0", name="ck_resumes_file_size_positive"),
        Index("idx_resumes_user_id", "user_id"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False)
    # Cached AI resume review (strengths, tailoring tips, roles to search); None until requested
    insights: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    # What the student is looking for (JobPreferences); None = no preference, match everything
    preferences: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    match_results: Mapped[list["MatchResult"]] = relationship(
        "MatchResult", back_populates="resume", cascade="all, delete-orphan"
    )
