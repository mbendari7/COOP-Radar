"""
Everything to do with accounts and signing in.

The routers stay thin and call these. Session tokens are 32 random bytes kept in
the session store (app/store.py) as session:<token> with a 7 day expiry that keeps
moving forward while you use the site.

Passwords are hashed with argon2id using the library defaults
  time_cost=2, memory_cost=65536 (64 MB), parallelism=1
That is plenty for a site this size.
"""

import secrets
from uuid import UUID

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.user import User
from app.store import Store

_ph = PasswordHasher()  # one shared hasher is safe and cheap to keep around
_SESSION_TTL = 60 * 60 * 24 * 7  # 7 days

# Slowing down password guessing
# 5 failed tries for one email within 15 minutes gets a 429.
# The counter lives in the session store next to the sessions
_RATE_PREFIX = "login_attempts:"
_MAX_ATTEMPTS = 5
_RATE_WINDOW = 60 * 15  # 15 minutes in seconds


async def _check_login_rate_limit(store: Store, email: str) -> None:
    """Add one to the tries for this email and answer 429 if it is over the limit."""
    key = f"{_RATE_PREFIX}{email}"
    count = await store.incr(key)
    if count == 1:
        # First try in this window so start the clock
        await store.expire(key, _RATE_WINDOW)
    if count > _MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "detail": "Too many login attempts. Try again in 15 minutes.",
                "code": "RATE_LIMITED",
            },
        )


async def _clear_login_rate_limit(store: Store, email: str) -> None:
    """Clear the tries counter after a good sign in."""
    await store.delete(f"{_RATE_PREFIX}{email}")


# Cookies

def set_session_cookie(response: Response, token: str) -> None:
    """Put the session cookie on the response after sign in or sign up."""
    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        # Secure by default. Browsers treat http://localhost as secure so local dev still works.
        # COOKIE_SECURE=false is only for clients that are not browsers, like the tests
        secure=get_settings().cookie_secure,
        samesite="lax",       # stops other sites from riding on the cookie
        path="/",
        max_age=_SESSION_TTL,
    )


def clear_session_cookie(response: Response) -> None:
    """Take the session cookie off the browser on sign out or account delete."""
    response.set_cookie(
        key="session",
        value="",
        httponly=True,
        secure=get_settings().cookie_secure,
        samesite="lax",
        path="/",
        max_age=0,
    )


# Sessions

async def _create_session(store: Store, user_id: UUID) -> str:
    """Make a new session and give back its token."""
    token = secrets.token_hex(32)  # 256 random bits
    key = f"session:{token}"
    await store.hset(key, "user_id", str(user_id))
    await store.expire(key, _SESSION_TTL)
    return token


# Account actions

async def register(
    db: AsyncSession,
    store: Store,
    email: str,
    password: str,
) -> tuple[User, str]:
    """
    Make a new account and sign in.

    Gives back the user and the session token.
    Answers 409 if the email is already taken.
    The email is saved in lowercase.
    """
    normalised = email.lower().strip()

    # Check the email is free before hashing so we do not waste the work
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

    token = await _create_session(store, user.id)
    return user, token


async def login(
    db: AsyncSession,
    store: Store,
    email: str,
    password: str,
) -> tuple[User, str]:
    """
    Check the email and password and sign in.

    Gives back the user and the session token.
    Answers the same 401 whether the email is unknown or the password is wrong
    so nobody can tell which emails have accounts.
    Answers 429 after 5 failed tries within 15 minutes.
    """
    normalised = email.lower().strip()

    # Check the limit before touching the database so timing gives nothing away either
    await _check_login_rate_limit(store, normalised)

    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"detail": "Invalid email or password", "code": "INVALID_CREDENTIALS"},
    )

    user = (
        await db.execute(select(User).where(User.email == normalised))
    ).scalar_one_or_none()

    if user is None:
        # Hash something anyway so the timing looks the same either way
        _ph.hash(password)
        raise invalid

    try:
        _ph.verify(user.hashed_password, password)
    except VerifyMismatchError:
        raise invalid from None

    # Good sign in so clear the counter
    await _clear_login_rate_limit(store, normalised)

    # Hash again if the argon2 settings changed. argon2-cffi tells us when
    if _ph.check_needs_rehash(user.hashed_password):
        user.hashed_password = _ph.hash(password)
        await db.commit()

    token = await _create_session(store, user.id)
    return user, token


async def logout(store: Store, token: str) -> None:
    """End a session right away. The next request with this cookie gets 401."""
    await store.delete(f"session:{token}")


async def change_password(
    db: AsyncSession,
    user: User,
    current_password: str,
    new_password: str,
) -> None:
    """
    Change a password after checking the current one.
    Answers 401 if the current password is wrong.
    """
    try:
        _ph.verify(user.hashed_password, current_password)
    except VerifyMismatchError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Current password is incorrect", "code": "WRONG_PASSWORD"},
        ) from exc

    user.hashed_password = _ph.hash(new_password)
    await db.commit()


async def delete_account(
    db: AsyncSession,
    store: Store,
    user: User,
    token: str,
    password: str,
) -> None:
    """
    Delete an account and everything tied to it for good.

    The database cascade removes saved jobs on its own.
    We delete the session first so nobody can sneak in a request
    in the tiny gap between clearing the cookie and deleting the row.
    Answers 401 if the password is wrong.
    """
    try:
        _ph.verify(user.hashed_password, password)
    except VerifyMismatchError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Current password is incorrect", "code": "WRONG_PASSWORD"},
        ) from exc

    # End the session before deleting the row
    await store.delete(f"session:{token}")
    await db.delete(user)
    await db.commit()
