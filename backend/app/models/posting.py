import enum
from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    DDL,
    TIMESTAMP,
    CheckConstraint,
    Computed,
    Date,
    Enum,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    event,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

# Postgres only allows IMMUTABLE functions in generated columns, and the built-in
# array_to_string() is merely STABLE. This one-line SQL wrapper is safe to declare
# IMMUTABLE for text[] input. Migration 0001 creates it too; the listener below makes
# Base.metadata.create_all() (used by the tests) create it before the postings table.
SKILLS_TO_TEXT_DDL = (
    "CREATE OR REPLACE FUNCTION coopradar_skills_text(text[]) RETURNS text "
    "LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$ SELECT array_to_string($1, ' ') $$"
)


class WorkMode(enum.StrEnum):
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
    change. The expression below mirrors migration 0001 exactly, so
    Base.metadata.create_all() (used by the test suite) builds the same column,
    and SQLAlchemy never tries to INSERT/UPDATE it.
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
        TIMESTAMP(timezone=True),
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

    # Weights: A = title, B = company + skills, C = description (title matches rank highest)
    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed(
            "setweight(to_tsvector('english', coalesce(title, '')), 'A') || "
            "setweight(to_tsvector('english', coalesce(company, '')), 'B') || "
            "setweight(to_tsvector('english', "
            "coalesce(coopradar_skills_text(skills), '')), 'B') || "
            "setweight(to_tsvector('english', coalesce(description, '')), 'C')",
            persisted=True,
        ),
        nullable=True,
    )

    # Feature 003 — ingestion source tracking
    source_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ingest_sources.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    low_confidence_fields: Mapped[dict[str, float]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

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
        # Feature 003 indexes
        Index("idx_postings_closed_at", "closed_at"),
        Index(
            "idx_postings_source_ref",
            "source_id",
            "source_ref",
            unique=True,
            postgresql_where=text("source_ref IS NOT NULL"),
        ),
    )


event.listen(
    Posting.__table__,
    "before_create",
    DDL(SKILLS_TO_TEXT_DDL),  # type: ignore[no-untyped-call]
)
