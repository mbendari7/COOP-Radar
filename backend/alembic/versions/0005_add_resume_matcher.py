"""add resumes and match_results tables for AI resume matcher

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-10
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resumes",
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
            unique=True,
        ),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False),
        sa.Column(
            "uploaded_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("file_size > 0", name="ck_resumes_file_size_positive"),
    )
    op.create_index("idx_resumes_user_id", "resumes", ["user_id"])

    op.create_table(
        "match_results",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "resume_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("resumes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "posting_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("postings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("score", sa.SmallInteger(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "ranked_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "score >= 0 AND score <= 100", name="ck_match_results_score_range"
        ),
        sa.UniqueConstraint(
            "resume_id", "posting_id", name="uq_match_results_resume_posting"
        ),
    )
    op.create_index(
        "idx_match_results_resume_score",
        "match_results",
        ["resume_id", sa.text("score DESC")],
    )


def downgrade() -> None:
    op.drop_table("match_results")
    op.drop_table("resumes")
