from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    TIMESTAMP,
    CheckConstraint,
    ForeignKey,
    Index,
    SmallInteger,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.resume import Resume


class MatchResult(Base):
    """
    One scored match between a resume and a posting, produced by the match pipeline.
    All rows for a given resume are replaced when a new upload triggers re-ranking.
    """

    __tablename__ = "match_results"
    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= 100", name="ck_match_results_score_range"),
        UniqueConstraint("resume_id", "posting_id", name="uq_match_results_resume_posting"),
        Index("idx_match_results_resume_score", "resume_id", text("score DESC")),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    resume_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
    )
    posting_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("postings.id", ondelete="CASCADE"),
        nullable=False,
    )
    score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    ranked_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    resume: Mapped["Resume"] = relationship(
        "Resume", back_populates="match_results"
    )
