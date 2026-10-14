"""Workable job search as an import source

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-14
"""

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

_ADAPTERS_OLD = (
    "'json_api','rss','csv','manual','greenhouse','lever','ashby','smartrecruiters',"
    "'workday','adzuna'"
)
_ADAPTERS_NEW = _ADAPTERS_OLD + ",'workable'"


def upgrade() -> None:
    op.drop_constraint("ck_ingest_sources_adapter_type", "ingest_sources", type_="check")
    op.create_check_constraint(
        "ck_ingest_sources_adapter_type", "ingest_sources", f"adapter_type IN ({_ADAPTERS_NEW})"
    )


def downgrade() -> None:
    op.execute("DELETE FROM ingest_sources WHERE adapter_type = 'workable'")
    op.drop_constraint("ck_ingest_sources_adapter_type", "ingest_sources", type_="check")
    op.create_check_constraint(
        "ck_ingest_sources_adapter_type", "ingest_sources", f"adapter_type IN ({_ADAPTERS_OLD})"
    )
