"""
A daily limit per person on actions that use the owner's AI, like resume uploads and questions.

On a public site every call on the owner's key costs the owner money, so each person
gets AI_DAILY_LIMIT actions per UTC day. 0 means no limit. The counters live in the
session store (app/store.py).
"""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status

from app.config import get_settings
from app.store import Store

_KEY_TTL = 60 * 60 * 48  # keep counters a little past the day they are for


async def consume_ai_quota(store: Store, user_id: UUID) -> None:
    """Count one AI action for this person. Answers 429 AI_LIMIT_REACHED when over the limit."""
    limit = get_settings().ai_daily_limit
    if limit <= 0:
        return
    key = f"ai_usage:{user_id}:{datetime.now(UTC).date().isoformat()}"
    count = await store.incr(key)
    if count == 1:
        await store.expire(key, _KEY_TTL)
    if count > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "detail": f"You've used today's {limit} AI actions. Try again tomorrow.",
                "code": "AI_LIMIT_REACHED",
            },
        )
