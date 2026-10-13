"""postings.country, grad_years and fields_of_study plus SmartRecruiters boards

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-12
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

_ADAPTERS_OLD = "'json_api','rss','csv','manual','greenhouse','lever','ashby'"
_ADAPTERS_NEW = _ADAPTERS_OLD + ",'smartrecruiters'"


def upgrade() -> None:
    # Every job so far came in with the Canada filter
    op.add_column(
        "postings", sa.Column("country", sa.String(length=2), server_default="CA", nullable=False)
    )
    op.add_column(
        "postings",
        sa.Column(
            "grad_years", postgresql.ARRAY(sa.SmallInteger()),
            server_default=sa.text("'{}'::smallint[]"), nullable=False,
        ),
    )
    op.add_column(
        "postings",
        sa.Column(
            "fields_of_study", postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"), nullable=False,
        ),
    )
    op.create_index("idx_postings_country", "postings", ["country"], unique=False)
    op.drop_constraint("ck_ingest_sources_adapter_type", "ingest_sources", type_="check")
    op.create_check_constraint(
        "ck_ingest_sources_adapter_type", "ingest_sources", f"adapter_type IN ({_ADAPTERS_NEW})"
    )


def downgrade() -> None:
    op.execute("DELETE FROM ingest_sources WHERE adapter_type = 'smartrecruiters'")
    op.drop_constraint("ck_ingest_sources_adapter_type", "ingest_sources", type_="check")
    op.create_check_constraint(
        "ck_ingest_sources_adapter_type", "ingest_sources", f"adapter_type IN ({_ADAPTERS_OLD})"
    )
    op.drop_index("idx_postings_country", table_name="postings")
    op.drop_column("postings", "fields_of_study")
    op.drop_column("postings", "grad_years")
    op.drop_column("postings", "country")
