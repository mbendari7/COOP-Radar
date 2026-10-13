"""
Tests for running with no Redis and no separate worker. The Postgres session store
(app/store.py) and the background jobs inside the app (app/jobs.py).
"""

import asyncio
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app import jobs
from app.config import get_settings
from app.jobs import enqueue as real_enqueue  # conftest patches app.jobs.enqueue in each test
from app.store import PostgresStore, create_store


@pytest.fixture
async def store(db_session: AsyncSession) -> PostgresStore:
    """A PostgresStore whose writes stay inside the test's transaction, which rolls back."""
    conn = await db_session.connection()
    factory = async_sessionmaker(
        bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    return PostgresStore(factory)


# Session store


async def test_hset_hget_round_trip(store: PostgresStore) -> None:
    await store.hset("session:abc", "user_id", "42")
    await store.hset("session:abc", "other", "x")  # adds to it and does not overwrite

    assert await store.hget("session:abc", "user_id") == "42"
    assert await store.hget("session:abc", "other") == "x"
    assert await store.hget("session:abc", "missing") is None
    assert await store.hget("session:nope", "user_id") is None


async def test_incr_counts_and_delete_resets(store: PostgresStore) -> None:
    assert await store.incr("rate:me") == 1
    assert await store.incr("rate:me") == 2
    await store.delete("rate:me")
    assert await store.incr("rate:me") == 1


async def test_expired_keys_behave_as_missing(store: PostgresStore) -> None:
    await store.hset("session:old", "user_id", "7")
    await store.incr("rate:old")
    await store.expire("session:old", -3600)
    await store.expire("rate:old", -3600)

    assert await store.hget("session:old", "user_id") is None
    assert await store.incr("rate:old") == 1  # the counter starts over like Redis

    await store.hset("session:gone", "user_id", "8")
    await store.expire("session:gone", -3600)
    assert await store.purge_expired() == 2  # session:old and session:gone
    assert await store.hget("session:gone", "user_id") is None


async def test_live_key_keeps_its_value_after_expire(store: PostgresStore) -> None:
    await store.hset("session:live", "user_id", "9")
    await store.expire("session:live", 3600)
    assert await store.hget("session:live", "user_id") == "9"


def test_create_store_uses_postgres_without_redis_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "redis_url", "")
    assert isinstance(create_store(), PostgresStore)


# Background jobs


async def test_enqueue_runs_job_in_background(monkeypatch: pytest.MonkeyPatch) -> None:
    job = AsyncMock()
    monkeypatch.setitem(jobs.JOBS, "test_job", job)

    real_enqueue("test_job", "a", "b")
    await asyncio.gather(*jobs._tasks)

    job.assert_awaited_once_with("a", "b")


async def test_failed_job_is_logged_not_raised(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(jobs.JOBS, "boom", AsyncMock(side_effect=RuntimeError("feed down")))

    real_enqueue("boom")
    await asyncio.gather(*jobs._tasks)  # this would raise if the error got out


def test_enqueue_unknown_job_raises() -> None:
    with pytest.raises(KeyError):
        real_enqueue("not_a_job")


async def test_run_due_sources_imports_each_due_source(monkeypatch: pytest.MonkeyPatch) -> None:
    run = AsyncMock()
    monkeypatch.setitem(jobs.JOBS, "run_source", run)
    monkeypatch.setattr(jobs, "_due_source_ids", AsyncMock(return_value=["s1", "s2"]))

    assert await jobs.run_due_sources() == 2
    assert [c.args for c in run.await_args_list] == [("s1",), ("s2",)]
