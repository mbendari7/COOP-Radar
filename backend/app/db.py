from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    """
    Shared declarative base for all ORM models.
    Importing this in alembic/env.py gives Alembic visibility into all tables.
    """
    pass


def _make_engine() -> AsyncEngine:
    """
    Build the async engine from settings.
    pool_pre_ping=True keeps connections fresh after a DB restart
    without us having to handle OperationalError manually.
    """
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        # Fail fast instead of hanging: Postgres cancels any statement running longer than
        # this, and the request returns the standard error shape (500) instead of timing out.
        connect_args={
            "server_settings": {"statement_timeout": str(settings.db_statement_timeout_ms)}
        },
        # echo=True is handy for debugging but too noisy in prod
        echo=False,
    )


# Module-level engine and session factory — created once at import time.
engine = _make_engine()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # avoid lazy-load errors after commit
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an AsyncSession for each request
    and closes it when the request is done (success or exception).
    """
    async with AsyncSessionLocal() as session:
        yield session
