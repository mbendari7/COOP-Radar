"""
Async Redis client factory and FastAPI dependency.

The pool is created once at application startup (via lifespan) and stored
on app.state.redis.  Every authenticated request reads/writes the session
hash from this single pool — no per-request connection overhead.
"""

from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import Request

from app.config import get_settings


def create_redis_pool() -> aioredis.Redis:  # type: ignore[type-arg]
    """
    Create an async Redis connection pool from the configured REDIS_URL.
    Called once in app lifespan startup; result stored on app.state.redis.
    """
    settings = get_settings()
    return aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )


async def get_redis(request: Request) -> AsyncGenerator[aioredis.Redis, None]:  # type: ignore[type-arg]
    """
    FastAPI dependency that yields the application-level Redis pool.
    Routes that need Redis declare: redis: aioredis.Redis = Depends(get_redis)
    """
    yield request.app.state.redis
