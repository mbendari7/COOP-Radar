"""add users.is_demo for one-click demo accounts

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-11
"""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
    )
    # Cleanup deletes old demo users by (is_demo, created_at)
    op.create_index("idx_users_demo_created", "users", ["is_demo", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_users_demo_created", table_name="users")
    op.drop_column("users", "is_demo")
