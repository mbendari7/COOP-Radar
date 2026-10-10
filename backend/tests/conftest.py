"""
Shared pytest fixtures.

We spin up a test database using the same DATABASE_URL but a separate schema
(or a test-only DB if configured) and reset it between test sessions.
Each test gets its own transaction that is rolled back at the end — this is
faster than truncating tables and keeps tests from interfering with each other.
"""

import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db import Base, get_db
from app.main import create_app
from app.redis import get_redis


# Use a separate test database to avoid stomping on dev data.
# The CI workflow sets DATABASE_URL to the test DB; locally you can
# set TEST_DATABASE_URL or it falls back to the configured DB.
def get_test_db_url() -> str:
    import os
    return os.getenv("TEST_DATABASE_URL", get_settings().database_url)


@pytest.fixture(scope="session")
def event_loop():  # type: ignore[override]
    """
    Use a single event loop for the whole test session.
    Without this, session-scoped async fixtures break with asyncio.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    """Create the test database schema once for the whole session."""
    engine = create_async_engine(get_test_db_url(), echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:  # type: ignore[type-arg]
    """
    Each test gets its own session with an open transaction that is rolled back
    after the test finishes.  This gives us complete isolation without re-creating
    the schema for every test.
    """
    session_factory = async_sessionmaker(bind=db_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


class _MockRedis:
    """In-memory Redis stub for tests — avoids needing a real Redis instance."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, str]] = {}
        self._counters: dict[str, int] = {}

    async def hset(self, key: str, field: str, value: str) -> None:
        self._store.setdefault(key, {})[field] = value

    async def hget(self, key: str, field: str) -> str | None:
        return self._store.get(key, {}).get(field)

    async def incr(self, key: str) -> int:
        self._counters[key] = self._counters.get(key, 0) + 1
        return self._counters[key]

    async def expire(self, key: str, ttl: int) -> None:
        pass

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)
        self._counters.pop(key, None)

    async def aclose(self) -> None:
        pass


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Async HTTP client wired to the FastAPI app.
    Overrides get_db and get_redis so tests are fully in-memory — no real
    DB commits, no real Redis instance required.
    """
    app = create_app()
    mock_redis = _MockRedis()

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    async def override_get_redis(request=None):  # type: ignore[override]
        yield mock_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis
    app.state.redis = mock_redis

    async with AsyncClient(
        transport=ASGITransport(app=app),  # type: ignore[arg-type]
        base_url="http://test",
    ) as ac:
        yield ac
