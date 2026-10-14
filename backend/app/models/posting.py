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

# Postgres only allows IMMUTABLE functions in generated columns and the built in
# array_to_string() is only STABLE. This tiny SQL wrapper is safe to call IMMUTABLE
# for text[] input. Migration 0001 makes it too and the listener below makes sure
# create_all() in the tests makes it before the postings table.
SKILLS_TO_TEXT_DDL = (
    "CREATE OR REPLACE FUNCTION coopradar_skills_text(text[]) RETURNS text "
    "LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$ SELECT array_to_string($1, ' ') $$"
)


SEASON_SQL = (
    "CASE WHEN term ~* '^winter' THEN 'winter' WHEN term ~* '^spring' THEN 'spring' "
    "WHEN term ~* '^summer' THEN 'summer' WHEN term ~* '^fall' THEN 'fall' END"
)
TERM_START_SQL = (
    "CASE WHEN term ~* '^(winter|spring|summer|fall) [0-9]{4}$' THEN make_date("
    "CAST(right(term, 4) AS integer), "
    "CASE WHEN term ~* '^winter' THEN 1 WHEN term ~* '^spring' THEN 3 "
    "WHEN term ~* '^summer' THEN 5 ELSE 9 END, 1) END"
)


class WorkMode(enum.StrEnum):
    """
    Saved as a Postgres ENUM called work_mode_enum so the database
    itself rejects bad values.
    The str mixin lets FastAPI send it as a plain string.
    """
    onsite = "onsite"
    hybrid = "hybrid"
    remote = "remote"


class Posting(Base):
    """
    One row for every co-op or internship job.

    search_vector is a generated tsvector column that Postgres keeps up to date
    on its own whenever the title, company, skills or description change.
    The expression below matches migration 0001 exactly so create_all() in the
    tests builds the same column, and SQLAlchemy never tries to write to it.
    """

    __tablename__ = "postings"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    company: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str] = mapped_column(Text, nullable=False)
    # Province code in Canada or state code in the US
    province: Mapped[str] = mapped_column(String(2), nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False, server_default="CA")
    work_mode: Mapped[WorkMode] = mapped_column(
        Enum(WorkMode, name="work_mode_enum"), nullable=False
    )
    # Like "Summer 2027", "Summer" or "Open" when the job does not say (app/ingest/terms.py)
    term: Mapped[str] = mapped_column(Text, nullable=False)
    # Postgres works these two out from term on its own. season is winter, spring, summer or
    # fall and term_start is the first day of the term, so jobs sort by when they start.
    # The expressions match migration 0011 exactly
    season: Mapped[str | None] = mapped_column(
        Text, Computed(SEASON_SQL, persisted=True), nullable=True
    )
    term_start: Mapped[date | None] = mapped_column(
        Date, Computed(TERM_START_SQL, persisted=True), nullable=True
    )

    # The check only allows the four normal co-op lengths. None means the job does not say
    duration_months: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    deadline: Mapped[date] = mapped_column(Date, nullable=False)
    posted_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        # The database fills this in so we never have to
        server_default=text("NOW()"),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # A Postgres text array with a GIN index so contains queries are fast
    skills: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'::text[]")
    )

    # Weights are A for title, B for company and skills, C for description. Title hits rank highest
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

    # Where the job was imported from
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

    # Read from the description when we import it (app/services/education.py).
    # The grad years the job asks for and the programs it names. Empty means it did not say
    grad_years: Mapped[list[int]] = mapped_column(
        ARRAY(SmallInteger), nullable=False, server_default=text("'{}'::smallint[]")
    )
    fields_of_study: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'::text[]")
    )

    __table_args__ = (
        CheckConstraint(
            "duration_months IN (4, 8, 12, 16)", name="ck_duration_months"
        ),
        # GIN indexes for full text search and array lookups
        Index("idx_postings_search_vector", "search_vector", postgresql_using="gin"),
        Index("idx_postings_skills", "skills", postgresql_using="gin"),
        # Normal indexes for sorting and exact filters
        Index("idx_postings_posted_at", "posted_at"),
        Index("idx_postings_deadline", "deadline"),
        Index("idx_postings_company", "company"),
        Index("idx_postings_title", "title"),
        Index("idx_postings_city", "city"),
        Index("idx_postings_province", "province"),
        Index("idx_postings_country", "country"),
        Index("idx_postings_term", "term"),
        Index("idx_postings_work_mode", "work_mode"),
        Index("idx_postings_duration", "duration_months"),
        Index("idx_postings_season", "season"),
        Index("idx_postings_term_start", "term_start"),
        # Indexes for import tracking
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
