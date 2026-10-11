"""
Shared FastAPI dependencies for authentication.

get_current_user — reads the session cookie, validates it against Redis,
returns the User ORM object, and resets the rolling TTL.  Raises 401 if
anything is missing or invalid.

get_optional_user — same logic but returns None instead of raising 401.
Used by routes that work for both authenticated and unauthenticated users
(e.g. GET /api/postings must work without login but can personalise when logged in).
"""

from uuid import UUID

import redis.asyncio as aioredis
from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.user import User
from app.redis import get_redis

_SESSION_TTL = 60 * 60 * 24 * 7  # 7 days in seconds


async def get_current_user(
    request: Request,
    session: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> User:
    """
    Resolve the session cookie to a User ORM object.

    Steps:
    1. Read the `session` cookie value (the raw 64-char hex token)
    2. Look up `session:<token>` in Redis — must contain `user_id`
    3. SELECT the User row from PostgreSQL
    4. Reset the Redis TTL (rolling 7-day expiry per FR-004)
    5. Return the User, or raise HTTP 401

    Raises HTTP 503 if Redis is unreachable (signals clients to retry).
    """
    not_auth = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"detail": "Not authenticated", "code": "NOT_AUTHENTICATED"},
    )

    if not session:
        raise not_auth

    redis_key = f"session:{session}"

    try:
        user_id = await redis.hget(redis_key, "user_id")
    except Exception as exc:  # noqa: BLE001 — any Redis failure means "retry later"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "detail": "Session store unavailable, please retry",
                "code": "SESSION_STORE_UNAVAILABLE",
            },
        ) from exc

    if not user_id:
        raise not_auth

    try:
        user = await db.get(User, UUID(str(user_id)))
    except ValueError:  # malformed id in Redis
        user = None

    if user is None:
        # Session key exists but user was deleted — clean up stale key
        await redis.delete(redis_key)
        raise not_auth

    # Reset rolling TTL so active users never get logged out unexpectedly
    await redis.expire(redis_key, _SESSION_TTL)

    return user


async def get_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Require the authenticated user to have is_admin = True.
    Raises HTTP 403 FORBIDDEN if the user is not an admin.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"detail": "Forbidden", "code": "FORBIDDEN"},
        )
    return current_user


async def get_optional_user(
    request: Request,
    session: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> User | None:
    """
    Like get_current_user but returns None instead of raising 401.
    Safe to use on public endpoints that benefit from knowing who's asking.
    """
    if not session:
        return None

    try:
        return await get_current_user(request=request, session=session, db=db, redis=redis)
    except HTTPException:
        return None
