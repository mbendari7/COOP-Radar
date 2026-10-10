"""
Authentication business logic.

All auth operations live here — routers stay thin and just call these
functions.  Session tokens are 32 random bytes (256-bit entropy) stored
in Redis as `session:<hex-token>` hashes with a 7-day rolling TTL.

Password hashing uses argon2id via argon2-cffi with library defaults:
  time_cost=2, memory_cost=65536 (64 MB), parallelism=1
These are adequate for a web app at this scale (Constitution III).
"""

import secrets
from uuid import UUID

import redis.asyncio as aioredis
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

_ph = PasswordHasher()  # singleton — thread-safe, cheap to keep
_SESSION_TTL = 60 * 60 * 24 * 7  # 7 days

# ── Login rate limiting ────────────────────────────────────────────────────────
# 5 failed attempts per email within a 15-minute window triggers a 429.
# Counter lives in Redis alongside sessions (same pool).
_RATE_PREFIX = "login_attempts:"
_MAX_ATTEMPTS = 5
_RATE_WINDOW = 60 * 15  # 15 minutes in seconds


async def _check_login_rate_limit(redis: aioredis.Redis, email: str) -> None:  # type: ignore[type-arg]
    """Increment the attempt counter for this email; raise 429 if over limit."""
    key = f"{_RATE_PREFIX}{email}"
    count = await redis.incr(key)
    if count == 1:
        # First attempt in this window — set the TTL
        await redis.expire(key, _RATE_WINDOW)
    if count > _MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "detail": "Too many login attempts. Try again in 15 minutes.",
                "code": "RATE_LIMITED",
            },
        )


async def _clear_login_rate_limit(redis: aioredis.Redis, email: str) -> None:  # type: ignore[type-arg]
    """Remove the attempt counter after a successful login."""
    await redis.delete(f"{_RATE_PREFIX}{email}")


# ── Cookie helpers ────────────────────────────────────────────────────────────

def set_session_cookie(response: Response, token: str) -> None:
    """Attach the session cookie to a response (login / register)."""
    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        secure=True,          # browsers only send over HTTPS; accepted over HTTP in dev
        samesite="lax",       # CSRF protection on same-origin navigations
        path="/",
        max_age=_SESSION_TTL,
    )


def clear_session_cookie(response: Response) -> None:
    """Remove the session cookie from the browser (logout / delete account)."""
    response.set_cookie(
        key="session",
        value="",
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
        max_age=0,
    )


# ── Session helpers ───────────────────────────────────────────────────────────

async def _create_session(redis: aioredis.Redis, user_id: UUID) -> str:  # type: ignore[type-arg]
    """Create a new Redis session and return the token."""
    token = secrets.token_hex(32)  # 256 bits of entropy
    key = f"session:{token}"
    await redis.hset(key, "user_id", str(user_id))
    await redis.expire(key, _SESSION_TTL)
    return token


# ── Auth operations ───────────────────────────────────────────────────────────

async def register(
    db: AsyncSession,
    redis: aioredis.Redis,  # type: ignore[type-arg]
    email: str,
    password: str,
) -> tuple[User, str]:
    """
    Create a new user account and start a session.

    Returns (user, session_token).
    Raises HTTP 409 if the email is already registered.
    Email is normalised to lowercase before storage (FR-003).
    """
    normalised = email.lower().strip()

    # Check uniqueness before hashing to avoid unnecessary work
    existing = (
        await db.execute(select(User).where(User.email == normalised))
    ).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"detail": "An account with this email already exists", "code": "EMAIL_TAKEN"},
        )

    hashed = _ph.hash(password)
    user = User(email=normalised, hashed_password=hashed)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = await _create_session(redis, user.id)
    return user, token


async def login(
    db: AsyncSession,
    redis: aioredis.Redis,  # type: ignore[type-arg]
    email: str,
    password: str,
) -> tuple[User, str]:
    """
    Verify credentials and start a session.

    Returns (user, session_token).
    Raises HTTP 401 with the same message whether the email is unknown or the
    password is wrong — preventing account enumeration (FR-014).
    Raises HTTP 429 after 5 failed attempts within a 15-minute window.
    """
    normalised = email.lower().strip()

    # Check rate limit before any DB work (prevents enumeration via timing too)
    await _check_login_rate_limit(redis, normalised)

    _INVALID = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"detail": "Invalid email or password", "code": "INVALID_CREDENTIALS"},
    )

    user = (
        await db.execute(select(User).where(User.email == normalised))
    ).scalar_one_or_none()

    if user is None:
        # Run a dummy hash to keep timing consistent (resist timing attacks)
        _ph.hash(password)
        raise _INVALID

    try:
        _ph.verify(user.hashed_password, password)
    except VerifyMismatchError:
        raise _INVALID

    # Successful login — clear the rate limit counter
    await _clear_login_rate_limit(redis, normalised)

    # Re-hash if argon2 parameters have changed (argon2-cffi handles this automatically)
    if _ph.check_needs_rehash(user.hashed_password):
        user.hashed_password = _ph.hash(password)
        await db.commit()

    token = await _create_session(redis, user.id)
    return user, token


async def logout(redis: aioredis.Redis, token: str) -> None:  # type: ignore[type-arg]
    """Invalidate a session immediately — next request with this cookie gets 401."""
    await redis.delete(f"session:{token}")


async def change_password(
    db: AsyncSession,
    user: User,
    current_password: str,
    new_password: str,
) -> None:
    """
    Update a user's password after verifying the current one.
    Raises HTTP 401 if current_password is wrong.
    """
    try:
        _ph.verify(user.hashed_password, current_password)
    except VerifyMismatchError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Current password is incorrect", "code": "WRONG_PASSWORD"},
        )

    user.hashed_password = _ph.hash(new_password)
    await db.commit()


async def delete_account(
    db: AsyncSession,
    redis: aioredis.Redis,  # type: ignore[type-arg]
    user: User,
    token: str,
    password: str,
) -> None:
    """
    Permanently delete a user account and all associated data.

    ON DELETE CASCADE in the DB removes saved_postings automatically.
    The Redis session is deleted first so the user can't make requests
    in the tiny window between the cookie being cleared and the DB delete.
    Raises HTTP 401 if password is wrong.
    """
    try:
        _ph.verify(user.hashed_password, password)
    except VerifyMismatchError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Current password is incorrect", "code": "WRONG_PASSWORD"},
        )

    # Invalidate session before deleting the row
    await redis.delete(f"session:{token}")
    await db.delete(user)
    await db.commit()
