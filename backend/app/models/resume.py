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
    The resume details and its text for one person.
    Each person keeps one resume at a time.
    We never keep the file itself, only the text we pulled out.
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
    # The saved AI resume review. None until someone asks for it
    insights: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    # What the student is looking for. None means no preference so everything can match
    preferences: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    match_results: Mapped[list["MatchResult"]] = relationship(
        "MatchResult", back_populates="resume", cascade="all, delete-orphan"
    )
