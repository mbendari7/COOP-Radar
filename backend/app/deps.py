"""
Shared FastAPI helpers for knowing who is signed in.

get_current_user reads the session cookie, checks it in the session store, gives back
the User and pushes the expiry forward again. Answers 401 if anything is off.

get_optional_user does the same but gives back None instead of a 401.
Public routes use it when they work for everyone but can do more for signed in people,
like the job list.
"""

from uuid import UUID

from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.user import User
from app.store import Store, get_store

_SESSION_TTL = 60 * 60 * 24 * 7  # 7 days in seconds


async def get_current_user(
    request: Request,
    session: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
    store: Store = Depends(get_store),
) -> User:
    """
    Turn the session cookie into a User.

    What happens
    1. Read the session cookie which holds a 64 character token
    2. Look up session:<token> in the store and get the user_id
    3. Load that User from Postgres
    4. Push the 7 day expiry forward again
    5. Give back the User or answer 401

    Answers 503 if the session store cannot be reached so the browser knows to retry.
    """
    not_auth = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"detail": "Not authenticated", "code": "NOT_AUTHENTICATED"},
    )

    if not session:
        raise not_auth

    session_key = f"session:{session}"

    try:
        user_id = await store.hget(session_key, "user_id")
    except Exception as exc:  # noqa: BLE001 any store problem means try again later
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
    except ValueError:  # the store had a broken id
        user = None

    if user is None:
        # The session is there but the user was deleted so clean up the old key
        await store.delete(session_key)
        raise not_auth

    # Push the expiry forward so active people never get signed out by surprise
    await store.expire(session_key, _SESSION_TTL)

    return user


async def get_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Only lets admins through.
    Answers 403 FORBIDDEN for everyone else.
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
    store: Store = Depends(get_store),
) -> User | None:
    """
    Same as get_current_user but gives back None instead of a 401.
    Fine for public endpoints that just like knowing who is asking.
    """
    if not session:
        return None

    try:
        return await get_current_user(request=request, session=session, db=db, store=store)
    except HTTPException:
        return None
