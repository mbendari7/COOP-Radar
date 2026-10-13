"""
One row for every student account.

Emails are saved in lowercase, and the service lowercases them before every
write and lookup. hashed_password is an argon2id hash and the real password
is never saved or logged.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import BOOLEAN, TIMESTAMP, Index, Text, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.saved_posting import SavedPosting


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    # The database keeps emails unique with the idx_users_email index
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("NOW()"), nullable=False
    )
    is_admin: Mapped[bool] = mapped_column(BOOLEAN, nullable=False, server_default=text("FALSE"))
    # A throwaway demo account that gets deleted 24 hours after it was made (services/demo.py)
    is_demo: Mapped[bool] = mapped_column(BOOLEAN, nullable=False, server_default=text("FALSE"))

    # Link back so user.saved_postings works when we need it
    saved_postings: Mapped[list["SavedPosting"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_users_email", "email", unique=True),
        Index("idx_users_demo_created", "is_demo", "created_at"),
    )
