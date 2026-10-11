"""IngestRun ORM model — one row per ingestion attempt for one source."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import TIMESTAMP, CheckConstraint, ForeignKey, Index, Integer, Text, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.ingest_source import IngestSource


class IngestRun(Base):
    __tablename__ = "ingest_runs"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    source_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ingest_sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    added: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    updated: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    closed: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    errors: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    error_log: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'::text[]")
    )

    source: Mapped["IngestSource"] = relationship(back_populates="runs")

    __table_args__ = (
        CheckConstraint(
            "status IN ('running','success','partial','failed')",
            name="ck_ingest_runs_status",
        ),
        Index("idx_ingest_runs_source_id", "source_id"),
        Index("idx_ingest_runs_started_at", text("started_at DESC")),
    )
