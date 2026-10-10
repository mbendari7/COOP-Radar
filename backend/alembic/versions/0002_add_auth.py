"""add users and saved_postings tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── application_status enum ──────────────────────────────────────────────
    # Four valid states for tracking an application's progress.
    # NULL in saved_postings.status means "no status set" (different from any value).
    status_enum = postgresql.ENUM(
        "applied", "interviewing", "offer", "rejected",
        name="application_status_enum",
        create_type=True,
    )
    status_enum.create(op.get_bind(), checkfirst=True)

    # ── users table ──────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        # Email stored lowercase — service layer normalises before every write/lookup
        sa.Column("email", sa.Text, nullable=False, unique=True),
        # argon2id hash — plaintext never stored
        sa.Column("hashed_password", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # Unique B-tree index on email — also the fast path for login lookups
    op.create_index("idx_users_email", "users", ["email"], unique=True)

    # ── saved_postings table ─────────────────────────────────────────────────
    op.create_table(
        "saved_postings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "posting_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("postings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "applied", "interviewing", "offer", "rejected",
                name="application_status_enum",
                create_type=False,  # already created above
            ),
            nullable=True,  # NULL = no status set
        ),
        sa.Column(
            "saved_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        # One save per (user, posting) pair — enables idempotent upsert via
        # INSERT … ON CONFLICT (user_id, posting_id) DO NOTHING
        sa.UniqueConstraint("user_id", "posting_id", name="ux_saved_postings_user_posting"),
    )

    # Index for listing a user's saved postings (most common read path)
    op.create_index("idx_saved_postings_user_id", "saved_postings", ["user_id"])
    # Index for checking whether a posting is saved (is_saved on postings list)
    op.create_index("idx_saved_postings_posting_id", "saved_postings", ["posting_id"])
    # Unique index on (user_id, posting_id) — enforces the constraint above
    op.create_index(
        "ux_saved_postings_user_posting_idx",
        "saved_postings",
        ["user_id", "posting_id"],
        unique=True,
    )
    # Index for filtering by status on the Saved page
    op.create_index("idx_saved_postings_status", "saved_postings", ["status"])
    # Descending index for default sort (most recently saved first)
    op.create_index(
        "idx_saved_postings_saved_at",
        "saved_postings",
        [sa.text("saved_at DESC")],
    )


def downgrade() -> None:
    # Drop in reverse order — saved_postings first (references users and postings)
    for idx in [
        "idx_saved_postings_saved_at",
        "idx_saved_postings_status",
        "ux_saved_postings_user_posting_idx",
        "idx_saved_postings_posting_id",
        "idx_saved_postings_user_id",
    ]:
        op.drop_index(idx, table_name="saved_postings")

    op.drop_table("saved_postings")

    op.drop_index("idx_users_email", table_name="users")
    op.drop_table("users")

    postgresql.ENUM(name="application_status_enum").drop(op.get_bind(), checkfirst=True)
