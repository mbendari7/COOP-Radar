"""Job Bank (jobbank.gc.ca) feeds as an import source

Revision ID: 0016
Revises: 0015
Create Date: 2026-10-29
"""

from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None

_ADAPTERS_OLD = (
    "'json_api','rss','csv','manual','greenhouse','lever','ashby','smartrecruiters',"
    "'workday','adzuna','workable','simplify','recruitee','bamboohr','rippling',"
    "'github_list','oracle','themuse','himalayas'"
)
_NEW = ("jobbank",)
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
