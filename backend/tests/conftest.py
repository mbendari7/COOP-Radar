"""
Shared pytest fixtures.

Database isolation: every test runs inside one outer transaction on a dedicated
connection. The session uses join_transaction_mode="create_savepoint", so when a
service calls `await db.commit()` only a SAVEPOINT is released — the outer
transaction is rolled back after the test and nothing leaks between tests.

The schema is rebuilt from the ORM models once per session (drop_all + create_all),
after enabling the `vector` extension the models rely on.
"""

import os

# Must be set before the app (and its cached settings) are imported: httpx won't
# send Secure cookies over the plain-http test transport.
os.environ.setdefault("COOKIE_SECURE", "false")

from collections.abc import AsyncGenerator, Callable  # noqa: E402
from typing import TYPE_CHECKING, Any  # noqa: E402
from unittest.mock import AsyncMock, MagicMock  # noqa: E402

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine  # noqa: E402

import app.models  # noqa: E402,F401 — registers every table on Base.metadata
from app.config import get_settings  # noqa: E402
from app.db import Base, get_db  # noqa: E402
from app.main import create_app  # noqa: E402
from app.store import get_store  # noqa: E402

get_settings.cache_clear()

if TYPE_CHECKING:
    from app.ai import AICredentials


def get_test_db_url() -> str:
    """CI points DATABASE_URL at a throwaway DB; locally you can set TEST_DATABASE_URL."""
    return os.getenv("TEST_DATABASE_URL", get_settings().database_url)


@pytest_asyncio.fixture(scope="session")
async def db_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create a fresh schema once for the whole test session."""
    engine = create_async_engine(get_test_db_url(), echo=False)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """A session whose commits are savepoints inside a transaction rolled back after the test."""
    async with db_engine.connect() as conn:
        outer = await conn.begin()
        session = AsyncSession(
            bind=conn,
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,
        )
        try:
            yield session
        finally:
            await session.close()
            await outer.rollback()


class MockRedis:
    """In-memory stand-in for the session store (app/store.py) — every command the app uses."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, str]] = {}
        self._counters: dict[str, int] = {}
        self.ttls: dict[str, int] = {}

    async def hset(self, key: str, field: str, value: str) -> None:
        self._store.setdefault(key, {})[field] = value

    async def hget(self, key: str, field: str) -> str | None:
        return self._store.get(key, {}).get(field)

    async def incr(self, key: str) -> int:
        self._counters[key] = self._counters.get(key, 0) + 1
        return self._counters[key]

    async def expire(self, key: str, ttl: int) -> None:
        self.ttls[key] = ttl

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)
        self._counters.pop(key, None)

    async def aclose(self) -> None:
        pass


TEST_AI_HEADERS = {"X-AI-Provider": "anthropic", "X-AI-Key": "sk-test-key", "X-AI-Model": "claude-test"}


@pytest.fixture
def mock_redis() -> MockRedis:
    return MockRedis()


@pytest.fixture(autouse=True)
def fresh_category_counts() -> None:
    """Each test seeds its own postings, so don't reuse job type counts between tests."""
    from app.services.postings import clear_category_counts_cache

    clear_category_counts_cache()


@pytest.fixture(autouse=True)
def fake_queue(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """
    Stop background jobs from really starting. Tests can assert on
    `fake_queue.enqueue` to check which jobs were started (see app/jobs.py).
    """
    queue = MagicMock()
    monkeypatch.setattr("app.jobs.enqueue", queue.enqueue)
    return queue


@pytest_asyncio.fixture
async def client(
    db_session: AsyncSession, mock_redis: MockRedis
) -> AsyncGenerator[AsyncClient, None]:
    """
    Async HTTP client wired to the FastAPI app, sharing the test's DB session
    and the in-memory Redis. The client keeps cookies, so register/login once
    and later requests are authenticated.
    """
    app = create_app()

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    async def override_get_store() -> AsyncGenerator[MockRedis, None]:
        yield mock_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_store] = override_get_store
    app.state.store = mock_redis

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        # Like a visitor who saved their own key on the AI key page (see app/ai.py)
        headers=TEST_AI_HEADERS,
    ) as ac:
        yield ac


# ── Claude mocks ──────────────────────────────────────────────────────────────


def text_message(text_value: str) -> MagicMock:
    """A fake Messages API response: a thinking block followed by one text block."""
    thinking = MagicMock(spec=["type", "thinking"], type="thinking", thinking="")
    text_block = MagicMock(spec=["type", "text"], type="text", text=text_value)
    return MagicMock(content=[thinking, text_block], stop_reason="end_turn")


@pytest.fixture
def mock_claude_create(monkeypatch: pytest.MonkeyPatch) -> Callable[[str], AsyncMock]:
    """Patch `client.messages.create` to return `text_value`. Returns the create mock."""

    def _install(text_value: str) -> AsyncMock:
        client = MagicMock()
        client.messages.create = AsyncMock(return_value=text_message(text_value))
        monkeypatch.setattr("anthropic.AsyncAnthropic", MagicMock(return_value=client))
        return client.messages.create

    return _install


@pytest.fixture
def mock_claude_stream(monkeypatch: pytest.MonkeyPatch) -> Callable[..., MagicMock]:
    """Patch Claude's `client.messages.stream` to stream `text_value` in small chunks."""

    def _install(text_value: str, stop_reason: str = "end_turn") -> MagicMock:
        async def text_stream() -> AsyncGenerator[str, None]:
            for i in range(0, len(text_value), 5):
                yield text_value[i : i + 5]

        stream: Any = MagicMock()
        stream.__aenter__ = AsyncMock(return_value=stream)
        stream.__aexit__ = AsyncMock(return_value=False)
        stream.text_stream = text_stream()
        stream.get_final_message = AsyncMock(return_value=MagicMock(stop_reason=stop_reason))

        client = MagicMock()
        client.messages.stream = MagicMock(return_value=stream)
        monkeypatch.setattr("anthropic.AsyncAnthropic", MagicMock(return_value=client))
        return client.messages.stream

    return _install


@pytest.fixture
def mock_embedding(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    """Patch OpenAI embedding generation with a deterministic vector."""
    mock = AsyncMock(return_value=[0.1] * 1536)
    monkeypatch.setattr("app.ingest.embed.generate_embedding", mock)
    return mock


@pytest.fixture
def test_creds() -> "AICredentials":
    """Visitor credentials for calling services directly (Claude, mocked)."""
    from app.ai import AICredentials

    return AICredentials("anthropic", "sk-test-key", "claude-test", "user")
