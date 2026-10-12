"""kv_store table: login sessions and counters without Redis

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-11
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "kv_store",
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column(
            "fields",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("counter", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_index("idx_kv_store_expires_at", "kv_store", ["expires_at"])


def downgrade() -> None:
    op.drop_index("idx_kv_store_expires_at", table_name="kv_store")
    op.drop_table("kv_store")
