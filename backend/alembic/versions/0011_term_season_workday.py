"""Season and term start on postings, length can be unknown, Workday and Adzuna sources

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-13
"""

import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

_ADAPTERS_OLD = "'json_api','rss','csv','manual','greenhouse','lever','ashby','smartrecruiters'"
_ADAPTERS_NEW = _ADAPTERS_OLD + ",'workday','adzuna'"

# Same text as SEASON_SQL and TERM_START_SQL in app/models/posting.py
_SEASON_SQL = (
    "CASE WHEN term ~* '^winter' THEN 'winter' WHEN term ~* '^spring' THEN 'spring' "
    "WHEN term ~* '^summer' THEN 'summer' WHEN term ~* '^fall' THEN 'fall' END"
)
_TERM_START_SQL = (
    "CASE WHEN term ~* '^(winter|spring|summer|fall) [0-9]{4}$' THEN make_date("
    "CAST(right(term, 4) AS integer), "
    "CASE WHEN term ~* '^winter' THEN 1 WHEN term ~* '^spring' THEN 3 "
    "WHEN term ~* '^summer' THEN 5 ELSE 9 END, 1) END"
)


def upgrade() -> None:
    op.alter_column("postings", "duration_months", existing_type=sa.SmallInteger(), nullable=True)
    # Imported jobs all got 4 months when the board did not say. Clear those so the next import
    # reads the real length from the description (app/ingest/terms.py) or leaves it unknown
    op.execute("UPDATE postings SET duration_months = NULL WHERE source_id IS NOT NULL")
    op.add_column(
        "postings",
        sa.Column("season", sa.Text(), sa.Computed(_SEASON_SQL, persisted=True), nullable=True),
    )
    op.add_column(
        "postings",
        sa.Column(
            "term_start", sa.Date(), sa.Computed(_TERM_START_SQL, persisted=True), nullable=True
        ),
    )
    op.create_index("idx_postings_season", "postings", ["season"], unique=False)
    op.create_index("idx_postings_term_start", "postings", ["term_start"], unique=False)
    op.drop_constraint("ck_ingest_sources_adapter_type", "ingest_sources", type_="check")
    op.create_check_constraint(
        "ck_ingest_sources_adapter_type", "ingest_sources", f"adapter_type IN ({_ADAPTERS_NEW})"
    )


def downgrade() -> None:
    op.execute("DELETE FROM ingest_sources WHERE adapter_type IN ('workday', 'adzuna')")
    op.drop_constraint("ck_ingest_sources_adapter_type", "ingest_sources", type_="check")
    op.create_check_constraint(
        "ck_ingest_sources_adapter_type", "ingest_sources", f"adapter_type IN ({_ADAPTERS_OLD})"
    )
    op.drop_index("idx_postings_term_start", table_name="postings")
    op.drop_index("idx_postings_season", table_name="postings")
    op.drop_column("postings", "term_start")
    op.drop_column("postings", "season")
    op.execute("UPDATE postings SET duration_months = 4 WHERE duration_months IS NULL")
    op.alter_column("postings", "duration_months", existing_type=sa.SmallInteger(), nullable=False)
