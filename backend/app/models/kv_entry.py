"""KVEntry ORM model — login sessions and counters when Redis isn't configured (app/store.py)."""

from datetime import datetime
from typing import Any

from sqlalchemy import TIMESTAMP, BigInteger, Index, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class KVEntry(Base):
    __tablename__ = "kv_store"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    fields: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    counter: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))
    expires_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    __table_args__ = (Index("idx_kv_store_expires_at", "expires_at"),)
