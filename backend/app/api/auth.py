"""
Auth router — register, login, logout.

Routes are thin: validate input via Pydantic, call the service, set/clear
the session cookie, return the result.  No business logic lives here.
"""

from fastapi import APIRouter, Cookie, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

import redis.asyncio as aioredis

from app.db import get_db
from app.deps import get_current_user
from app.redis import get_redis
from app.schemas.auth import LoginIn, RegisterIn, UserOut
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterIn,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),  # type: ignore[type-arg]
) -> UserOut:
    """
    Create a new account and start a session.
    Returns 409 if the email is already registered.
    """
    user, token = await auth_service.register(db, redis, body.email, body.password)
    auth_service.set_session_cookie(response, token)
    return UserOut.model_validate(user)


@router.post("/login", response_model=UserOut, status_code=status.HTTP_200_OK)
async def login(
    body: LoginIn,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),  # type: ignore[type-arg]
) -> UserOut:
    """
    Authenticate and start a session.
    Returns 401 with the same message for unknown email or wrong password (FR-014).
    """
    user, token = await auth_service.login(db, redis, body.email, body.password)
    auth_service.set_session_cookie(response, token)
    return UserOut.model_validate(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    session: str | None = Cookie(default=None),
    _user=Depends(get_current_user),  # 401 if not authenticated
    redis: aioredis.Redis = Depends(get_redis),  # type: ignore[type-arg]
) -> None:
    """Invalidate the session immediately and clear the browser cookie."""
    if session:
        await auth_service.logout(redis, session)
    auth_service.clear_session_cookie(response)
