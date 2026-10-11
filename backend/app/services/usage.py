"""
Per-user daily limit on AI-backed actions (resume uploads and Q&A questions).

On a public site every Claude/OpenAI call is billed to the site owner, so each user
gets AI_DAILY_LIMIT actions per UTC day (0 = unlimited). Counters live in Redis.
"""

from datetime import UTC, datetime
from uuid import UUID

import redis.asyncio as aioredis
from fastapi import HTTPException, status

from app.config import get_settings

_KEY_TTL = 60 * 60 * 48  # keep counters a little past the day they belong to


async def consume_ai_quota(redis: aioredis.Redis, user_id: UUID) -> None:
    """Count one AI action for this user; raise 429 AI_LIMIT_REACHED when over the limit."""
    limit = get_settings().ai_daily_limit
    if limit <= 0:
        return
    key = f"ai_usage:{user_id}:{datetime.now(UTC).date().isoformat()}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, _KEY_TTL)
    if count > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "detail": f"You've used today's {limit} AI actions. Try again tomorrow.",
                "code": "AI_LIMIT_REACHED",
            },
        )
