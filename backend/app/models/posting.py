import enum
from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    ARRAY,
    CheckConstraint,
    Date,
    Enum,
    Index,
    SmallInteger,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class WorkMode(str, enum.Enum):
    """
    Stored as a PostgreSQL ENUM type (work_mode_enum) so the DB enforces
    valid values without needing an application-layer check.
    str mixin means FastAPI can serialise it as a plain string.
    """
    onsite = "onsite"
    hybrid = "hybrid"
    remote = "remote"


class Posting(Base):
    """
    One row per co-op/internship posting.

    search_vector is a GENERATED ALWAYS AS STORED tsvector column — PostgreSQL
    keeps it in sync automatically whenever title/company/skills/description
    change.  The actual GENERATED expression is in the migration (not here)
    because SQLAlchemy doesn't write GENERATED columns via autogenerate.
    """

    __tablename__ = "postings"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    company: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str] = mapped_column(Text, nullable=False)
    province: Mapped[str] = mapped_column(String(2), nullable=False)
    work_mode: Mapped[WorkMode] = mapped_column(
        Enum(WorkMode, name="work_mode_enum"), nullable=False
    )
    term: Mapped[str] = mapped_column(Text, nullable=False)

    # CHECK constraint enforces only the four valid co-op durations
    duration_months: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    deadline: Mapped[date] = mapped_column(Date, nullable=False)
    posted_at: Mapped[datetime] = mapped_column(
        # server_default lets the DB fill this in; we don't have to set it manually
        server_default=text("NOW()"),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # TEXT[] — stored as a Postgres array; GIN index supports fast @> (contains) queries
    skills: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'::text[]")
    )

    # Populated by the GENERATED expression in the migration.
    # Mapped as nullable so SQLAlchemy doesn't try to INSERT it.
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "duration_months IN (4, 8, 12, 16)", name="ck_duration_months"
        ),
        # GIN indexes for full-text and array containment queries
        Index("idx_postings_search_vector", "search_vector", postgresql_using="gin"),
        Index("idx_postings_skills", "skills", postgresql_using="gin"),
        # B-tree indexes for sorting and equality filters
        Index("idx_postings_posted_at", "posted_at"),
        Index("idx_postings_deadline", "deadline"),
        Index("idx_postings_company", "company"),
        Index("idx_postings_title", "title"),
        Index("idx_postings_city", "city"),
        Index("idx_postings_province", "province"),
        Index("idx_postings_term", "term"),
        Index("idx_postings_work_mode", "work_mode"),
        Index("idx_postings_duration", "duration_months"),
    )
