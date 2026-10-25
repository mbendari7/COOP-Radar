"""One row for every place we import jobs from."""

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import BOOLEAN, TIMESTAMP, CheckConstraint, Index, Integer, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.ingest_run import IngestRun


class IngestSource(Base):
    __tablename__ = "ingest_sources"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    adapter_type: Mapped[str] = mapped_column(Text, nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    enabled: Mapped[bool] = mapped_column(BOOLEAN, nullable=False, server_default=text("TRUE"))
    auto_paused: Mapped[bool] = mapped_column(BOOLEAN, nullable=False, server_default=text("FALSE"))
    consecutive_failures: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    last_run_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("NOW()"), nullable=False
    )

    runs: Mapped[list["IngestRun"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "adapter_type IN ('json_api','rss','csv','manual','greenhouse','lever','ashby',"
            "'smartrecruiters','workday','adzuna','workable','simplify','recruitee','bamboohr',"
            "'rippling','github_list','oracle','themuse','himalayas')",
            name="ck_ingest_sources_adapter_type",
        ),
        Index("idx_ingest_sources_enabled", "enabled", "auto_paused"),
    )
