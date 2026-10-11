"""
Auth router — register, login, logout.

Routes are thin: validate input via Pydantic, call the service, set/clear
the session cookie, return the result.  No business logic lives here.
"""

import redis.asyncio as aioredis
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db
from app.deps import get_current_user
from app.models.user import User
from app.redis import get_redis
from app.schemas.auth import LoginIn, RegisterIn, UserOut
from app.services import auth as auth_service
from app.services.demo import create_demo_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterIn,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
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
    redis: aioredis.Redis = Depends(get_redis),
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
    _user: User = Depends(get_current_user),  # 401 if not authenticated
    redis: aioredis.Redis = Depends(get_redis),
) -> None:
    """Invalidate the session immediately and clear the browser cookie."""
    if session:
        await auth_service.logout(redis, session)
    auth_service.clear_session_cookie(response)


@router.post("/demo", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def demo_login(
    request: Request,
    response: Response,
    x_forwarded_for: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> UserOut:
    """
    "Try the demo": create a private, pre-filled demo account and log into it.
    Returns 404 DEMO_DISABLED when DEMO_ENABLED=false; 429 after 10 per IP per hour.
    """
    if not get_settings().demo_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "Demo accounts are turned off.", "code": "DEMO_DISABLED"},
        )
    peer = request.client.host if request.client else None
    user, token = await create_demo_user(db, redis, x_forwarded_for, peer)
    auth_service.set_session_cookie(response, token)
    return UserOut.model_validate(user)
