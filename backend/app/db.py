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
    Base class for every database model.
    alembic/env.py imports it so Alembic can see all the tables.
    """
    pass


def _make_engine() -> AsyncEngine:
    """
    Build the async database engine from settings.
    pool_pre_ping keeps connections fresh after the database restarts
    so we do not have to catch those errors ourselves.
    """
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        # Fail fast instead of hanging. Postgres stops any query that runs longer than this
        # and the request gets our normal error shape instead of timing out
        connect_args={
            "server_settings": {"statement_timeout": str(settings.db_statement_timeout_ms)}
        },
        # echo=True helps when debugging but it is far too noisy in production
        echo=False,
    )


# One engine and session factory made once when the module loads
engine = _make_engine()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # so reading fields after commit does not blow up
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Gives each request its own database session
    and closes it when the request is done, even if it failed.
    """
    async with AsyncSessionLocal() as session:
        yield session
