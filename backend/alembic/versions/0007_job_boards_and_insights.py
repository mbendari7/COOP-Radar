"""career-board source types (greenhouse, lever, ashby) and cached resume insights

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-11
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

_OLD = "adapter_type IN ('json_api','rss','csv','manual')"
_NEW = "adapter_type IN ('json_api','rss','csv','manual','greenhouse','lever','ashby')"


def upgrade() -> None:
    op.drop_constraint("ck_ingest_sources_adapter_type", "ingest_sources", type_="check")
    op.create_check_constraint("ck_ingest_sources_adapter_type", "ingest_sources", _NEW)
    op.add_column("resumes", sa.Column("insights", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("resumes", "insights")
    op.execute(
        "DELETE FROM ingest_sources WHERE adapter_type IN ('greenhouse','lever','ashby')"
    )
    op.drop_constraint("ck_ingest_sources_adapter_type", "ingest_sources", type_="check")
    op.create_check_constraint("ck_ingest_sources_adapter_type", "ingest_sources", _OLD)
