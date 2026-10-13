"""
A small key value store for login sessions and rate limit counters.

By default it lives in Postgres in the kv_store table, so the site needs one database
and nothing else. Set REDIS_URL to use Redis instead. Same commands, just faster when
traffic is heavy.

We only need the few Redis commands the app uses
  hset and hget   session:<token> holds the user_id
  incr            rate limit and AI quota counters
  expire          rolling expiry times
  delete          sign out and cleanup

It is made once at startup and kept on app.state.store.
Routes get it with  store: Store = Depends(get_store)
"""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol, cast

from fastapi import Request
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import get_settings
from app.models.kv_entry import KVEntry


class Store(Protocol):
    async def hget(self, key: str, field: str) -> str | None: ...
    async def hset(self, key: str, field: str, value: str) -> Any: ...
    async def incr(self, key: str) -> int: ...
    async def expire(self, key: str, seconds: int) -> Any: ...
    async def delete(self, key: str) -> Any: ...
    async def aclose(self) -> None: ...


def _live(key: str) -> Any:
    """WHERE clause for this key when it has not expired."""
    return (KVEntry.key == key) & or_(
        KVEntry.expires_at.is_(None), KVEntry.expires_at > func.now()
    )


class PostgresStore:
    """The Store commands on top of one small Postgres table. Each call is its own transaction."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = session_factory

    async def _drop_if_expired(self, db: AsyncSession, key: str) -> None:
        # An expired key acts like it was never there, same as Redis
        await db.execute(
            delete(KVEntry).where(KVEntry.key == key, KVEntry.expires_at <= func.now())
        )

    async def hget(self, key: str, field: str) -> str | None:
        async with self._sessions() as db:
            fields = (await db.execute(select(KVEntry.fields).where(_live(key)))).scalar()
        return None if fields is None else fields.get(field)

    async def hset(self, key: str, field: str, value: str) -> None:
        async with self._sessions() as db:
            await self._drop_if_expired(db, key)
            stmt = pg_insert(KVEntry).values(key=key, fields={field: value})
            stmt = stmt.on_conflict_do_update(
                index_elements=[KVEntry.key],
                set_={"fields": KVEntry.fields.op("||")(stmt.excluded.fields)},
            )
            await db.execute(stmt)
            await db.commit()

    async def incr(self, key: str) -> int:
        async with self._sessions() as db:
            await self._drop_if_expired(db, key)
            upsert = (
                pg_insert(KVEntry)
                .values(key=key, counter=1)
                .on_conflict_do_update(
                    index_elements=[KVEntry.key], set_={"counter": KVEntry.counter + 1}
                )
                .returning(KVEntry.counter)
            )
            count = (await db.execute(upsert)).scalar_one()
            await db.commit()
        return int(count)

    async def expire(self, key: str, seconds: int) -> None:
        async with self._sessions() as db:
            await db.execute(
                update(KVEntry)
                .where(_live(key))
                .values(expires_at=datetime.now(UTC) + timedelta(seconds=seconds))
            )
            await db.commit()

    async def delete(self, key: str) -> None:
        async with self._sessions() as db:
            await db.execute(delete(KVEntry).where(KVEntry.key == key))
            await db.commit()

    async def purge_expired(self) -> int:
        """Delete every expired key. The background scheduler calls this."""
        async with self._sessions() as db:
            result = await db.execute(delete(KVEntry).where(KVEntry.expires_at <= func.now()))
            await db.commit()
        return int(getattr(result, "rowcount", 0) or 0)

    async def aclose(self) -> None:
        pass


def create_store() -> Store:
    """Redis when REDIS_URL is set and the Postgres table otherwise."""
    settings = get_settings()
    if settings.redis_url:
        import redis.asyncio as aioredis

        return cast(
            Store,
            aioredis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True),
        )
    from app.db import AsyncSessionLocal

    return PostgresStore(AsyncSessionLocal)


async def get_store(request: Request) -> AsyncGenerator[Store, None]:
    """Gives routes the one shared store."""
    yield request.app.state.store
