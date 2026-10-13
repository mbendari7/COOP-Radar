"""add ingestion tables, pgvector, and admin flag

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-10
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # users.is_admin
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
    )

    # ingest_sources
    op.create_table(
        "ingest_sources",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("adapter_type", sa.Text(), nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("auto_paused", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column(
            "consecutive_failures", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("last_run_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "adapter_type IN ('json_api','rss','csv','manual')",
            name="ck_ingest_sources_adapter_type",
        ),
    )
    op.create_index("idx_ingest_sources_enabled", "ingest_sources", ["enabled", "auto_paused"])

    # ingest_runs
    op.create_table(
        "ingest_runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ingest_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("finished_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("added", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("updated", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("closed", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("errors", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "error_log",
            sa.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.CheckConstraint(
            "status IN ('running','success','partial','failed')",
            name="ck_ingest_runs_status",
        ),
    )
    op.create_index("idx_ingest_runs_source_id", "ingest_runs", ["source_id"])
    op.create_index(
        "idx_ingest_runs_started_at", "ingest_runs", [sa.text("started_at DESC")]
    )

    # skills
    op.create_table(
        "skills",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.Text(), nullable=False, unique=True),
        sa.Column(
            "aliases", sa.ARRAY(sa.Text()), nullable=False, server_default=sa.text("'{}'")
        ),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("idx_skills_name", "skills", ["name"], unique=True)
    op.create_index("idx_skills_aliases", "skills", ["aliases"], postgresql_using="gin")

    # New columns on postings
    op.add_column(
        "postings",
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ingest_sources.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column("postings", sa.Column("source_ref", sa.Text(), nullable=True))
    op.add_column("postings", sa.Column("closed_at", sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column(
        "postings",
        sa.Column(
            "low_confidence_fields",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )
    op.create_index("idx_postings_closed_at", "postings", ["closed_at"])
    op.create_index(
        "idx_postings_source_ref",
        "postings",
        ["source_id", "source_ref"],
        unique=True,
        postgresql_where=sa.text("source_ref IS NOT NULL"),
    )

    # posting_embeddings, the vector table
    op.create_table(
        "posting_embeddings",
        sa.Column(
            "posting_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("postings.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("embedding", sa.Text(), nullable=False),  # swapped for the real type below
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column(
            "generated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    # Swap the text placeholder column for the real vector type
    op.execute("ALTER TABLE posting_embeddings ALTER COLUMN embedding TYPE vector(1536) USING embedding::vector(1536)")
    # HNSW index so closest match lookups stay fast
    op.execute(
        "CREATE INDEX idx_posting_embeddings_hnsw ON posting_embeddings "
        "USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_posting_embeddings_hnsw")
    op.drop_table("posting_embeddings")
    op.drop_index("idx_postings_source_ref", table_name="postings")
    op.drop_index("idx_postings_closed_at", table_name="postings")
    op.drop_column("postings", "low_confidence_fields")
    op.drop_column("postings", "closed_at")
    op.drop_column("postings", "source_ref")
    op.drop_column("postings", "source_id")
    op.drop_index("idx_skills_aliases", table_name="skills")
    op.drop_index("idx_skills_name", table_name="skills")
    op.drop_table("skills")
    op.drop_index("idx_ingest_runs_started_at", table_name="ingest_runs")
    op.drop_index("idx_ingest_runs_source_id", table_name="ingest_runs")
    op.drop_table("ingest_runs")
    op.drop_index("idx_ingest_sources_enabled", table_name="ingest_sources")
    op.drop_table("ingest_sources")
    op.drop_column("users", "is_admin")
    op.execute("DROP EXTENSION IF EXISTS vector")
