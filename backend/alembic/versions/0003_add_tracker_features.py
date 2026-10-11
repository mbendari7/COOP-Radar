"""add application_events table and last_status_at column

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-10
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── last_status_at column on saved_postings ──────────────────────────────
    # Populated whenever the application status changes; used for sorting by
    # "last updated" on the tracker table view.
    op.add_column(
        "saved_postings",
        sa.Column(
            "last_status_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )

    # ── application_events table ─────────────────────────────────────────────
    # One row per status change, storing the new status, an optional note, and
    # an optional user-supplied date (e.g. the date of an interview).
    op.create_table(
        "application_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "saved_posting_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("saved_postings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "saved", "applying", "applied", "interview",
                "offer", "rejected", "withdrawn",
                name="application_status_enum",
                create_type=False,  # enum already created in 0002
            ),
            nullable=False,
        ),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("event_date", sa.DATE, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # Index for fetching all events for a saved posting (most common read path)
    op.create_index(
        "idx_application_events_saved_posting_id",
        "application_events",
        ["saved_posting_id"],
    )
    # Descending index to efficiently fetch the most recent events first
    op.create_index(
        "idx_application_events_created_at",
        "application_events",
        [sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("idx_application_events_created_at", table_name="application_events")
    op.drop_index("idx_application_events_saved_posting_id", table_name="application_events")
    op.drop_table("application_events")
    op.drop_column("saved_postings", "last_status_at")
