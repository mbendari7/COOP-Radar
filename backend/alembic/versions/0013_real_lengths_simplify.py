"""Real job lengths in months, when we first saw each job, and Simplify's lists as a source

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-16
"""

import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

_ADAPTERS_OLD = (
    "'json_api','rss','csv','manual','greenhouse','lever','ashby','smartrecruiters',"
    "'workday','adzuna','workable'"
)
_ADAPTERS_NEW = _ADAPTERS_OLD + ",'simplify'"


def upgrade() -> None:
    # Lengths were rounded to 4, 8, 12 or 16 months, so a 6 month job showed as 8. Now we keep
    # the length the job states. Imported jobs get their real length on the next import run
    op.drop_constraint("ck_duration_months", "postings", type_="check")
    op.create_check_constraint("ck_duration_months", "postings", "duration_months BETWEEN 2 AND 24")
    # Jobs we already have count as first seen when they were posted
    op.add_column(
        "postings",
        sa.Column(
            "first_seen_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.execute("UPDATE postings SET first_seen_at = LEAST(posted_at, NOW())")
    op.create_index("idx_postings_first_seen_at", "postings", ["first_seen_at"], unique=False)
    op.drop_constraint("ck_ingest_sources_adapter_type", "ingest_sources", type_="check")
    op.create_check_constraint(
        "ck_ingest_sources_adapter_type", "ingest_sources", f"adapter_type IN ({_ADAPTERS_NEW})"
    )


def downgrade() -> None:
    op.drop_index("idx_postings_first_seen_at", table_name="postings")
    op.drop_column("postings", "first_seen_at")
    op.execute("DELETE FROM ingest_sources WHERE adapter_type = 'simplify'")
    op.drop_constraint("ck_ingest_sources_adapter_type", "ingest_sources", type_="check")
    op.create_check_constraint(
        "ck_ingest_sources_adapter_type", "ingest_sources", f"adapter_type IN ({_ADAPTERS_OLD})"
    )
    op.drop_constraint("ck_duration_months", "postings", type_="check")
    op.execute(
        "UPDATE postings SET duration_months = CASE "
        "WHEN duration_months <= 5 THEN 4 WHEN duration_months <= 9 THEN 8 "
        "WHEN duration_months <= 14 THEN 12 ELSE 16 END WHERE duration_months IS NOT NULL"
    )
    op.create_check_constraint(
        "ck_duration_months", "postings", "duration_months IN (4, 8, 12, 16)"
    )
