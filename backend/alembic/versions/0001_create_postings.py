"""create postings table

Revision ID: 0001
Revises:
Create Date: 2026-10-10
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


# Generated columns can only call IMMUTABLE functions and array_to_string() is STABLE,
# so we wrap it. Has to match SKILLS_TO_TEXT_DDL in app/models/posting.py
SKILLS_TO_TEXT_DDL = (
    "CREATE OR REPLACE FUNCTION coopradar_skills_text(text[]) RETURNS text "
    "LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$ SELECT array_to_string($1, ' ') $$"
)


def upgrade() -> None:
    op.execute(SKILLS_TO_TEXT_DDL)

    # Make the work_mode enum first since the table below uses it.
    # checkfirst=True means no error if this migration runs twice by accident
    work_mode_enum = postgresql.ENUM(
        "onsite", "hybrid", "remote",
        name="work_mode_enum",
        create_type=True,
    )
    work_mode_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "postings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("company", sa.Text, nullable=False),
        sa.Column("city", sa.Text, nullable=False),
        sa.Column("province", sa.String(2), nullable=False),
        sa.Column(
            "work_mode",
            postgresql.ENUM(
                "onsite", "hybrid", "remote",
                name="work_mode_enum",
                create_type=False,  # already made above
            ),
            nullable=False,
        ),
        sa.Column("term", sa.Text, nullable=False),
        sa.Column("duration_months", sa.SmallInteger, nullable=False),
        sa.Column("deadline", sa.Date, nullable=False),
        sa.Column(
            "posted_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("source_url", sa.Text, nullable=True),
        sa.Column(
            "skills",
            postgresql.ARRAY(sa.Text),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        # A stored generated column keeps search_vector up to date on its own.
        # The weights are A for title, B for company and skills and C for description
        # so title matches rank higher
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR,
            sa.Computed(
                """
                setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
                setweight(to_tsvector('english', coalesce(company, '')), 'B') ||
                setweight(to_tsvector('english', coalesce(coopradar_skills_text(skills), '')), 'B') ||
                setweight(to_tsvector('english', coalesce(description, '')), 'C')
                """,
                persisted=True,  # STORED means it is worked out once on write and not on every read
            ),
            nullable=True,
        ),
        sa.CheckConstraint("duration_months IN (4, 8, 12, 16)", name="ck_duration_months"),
    )

    # GIN index for full text search, very fast for tsvector queries
    op.create_index(
        "idx_postings_search_vector", "postings", ["search_vector"],
        postgresql_using="gin",
    )
    # GIN index for has all these skills queries
    op.create_index(
        "idx_postings_skills", "postings", ["skills"],
        postgresql_using="gin",
    )
    # Normal indexes for sort columns and exact filters
    op.create_index("idx_postings_posted_at", "postings", ["posted_at"])
    op.create_index("idx_postings_deadline", "postings", ["deadline"])
    op.create_index("idx_postings_company", "postings", ["company"])
    op.create_index("idx_postings_title", "postings", ["title"])
    op.create_index("idx_postings_city", "postings", ["city"])
    op.create_index("idx_postings_province", "postings", ["province"])
    op.create_index("idx_postings_term", "postings", ["term"])
    op.create_index("idx_postings_work_mode", "postings", ["work_mode"])
    op.create_index("idx_postings_duration", "postings", ["duration_months"])


def downgrade() -> None:
    # Drop the indexes first, then the table, then the custom type.
    # Order matters because the type cannot go while the table still uses it
    for idx in [
        "idx_postings_duration", "idx_postings_work_mode", "idx_postings_term",
        "idx_postings_province", "idx_postings_city", "idx_postings_title",
        "idx_postings_company", "idx_postings_deadline", "idx_postings_posted_at",
        "idx_postings_skills", "idx_postings_search_vector",
    ]:
        op.drop_index(idx, table_name="postings")

    op.drop_table("postings")

    postgresql.ENUM(name="work_mode_enum").drop(op.get_bind(), checkfirst=True)
    op.execute("DROP FUNCTION IF EXISTS coopradar_skills_text(text[])")
