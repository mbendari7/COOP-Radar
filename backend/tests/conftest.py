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


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Async HTTP client wired to the FastAPI app.
    Overrides the get_db dependency so every request in a test uses the
    same rolled-back session — changes made in the test are visible to the
    request but never committed to the real DB.
    """
    app = create_app()

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),  # type: ignore[arg-type]
        base_url="http://test",
    ) as ac:
        yield ac
