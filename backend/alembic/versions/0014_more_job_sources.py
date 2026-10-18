"""Recruitee, BambooHR, Rippling, Oracle career sites and GitHub job lists as import sources

Revision ID: 0014
Revises: 0013
Create Date: 2026-10-16
"""

from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

_ADAPTERS_OLD = (
    "'json_api','rss','csv','manual','greenhouse','lever','ashby','smartrecruiters',"
    "'workday','adzuna','workable','simplify'"
)
_NEW = ("recruitee", "bamboohr", "rippling", "github_list", "oracle")
_ADAPTERS_NEW = _ADAPTERS_OLD + "," + ",".join(f"'{a}'" for a in _NEW)


def upgrade() -> None:
    op.drop_constraint("ck_ingest_sources_adapter_type", "ingest_sources", type_="check")
    op.create_check_constraint(
        "ck_ingest_sources_adapter_type", "ingest_sources", f"adapter_type IN ({_ADAPTERS_NEW})"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM ingest_sources WHERE adapter_type IN ("
        + ",".join(f"'{a}'" for a in _NEW) + ")"
    )
    op.drop_constraint("ck_ingest_sources_adapter_type", "ingest_sources", type_="check")
    op.create_check_constraint(
        "ck_ingest_sources_adapter_type", "ingest_sources", f"adapter_type IN ({_ADAPTERS_OLD})"
    )
