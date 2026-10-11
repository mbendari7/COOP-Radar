"""
User ORM model.

One row per registered student.  Email is stored lowercase (normalised
at the service layer before every write and lookup).  hashed_password
is an argon2id hash — the plaintext is never stored or logged.
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
    # Unique constraint enforced in DB via idx_users_email unique index
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("NOW()"), nullable=False
    )
    is_admin: Mapped[bool] = mapped_column(BOOLEAN, nullable=False, server_default=text("FALSE"))

    # Back-reference so we can access user.saved_postings if needed
    saved_postings: Mapped[list["SavedPosting"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("idx_users_email", "email", unique=True),)
