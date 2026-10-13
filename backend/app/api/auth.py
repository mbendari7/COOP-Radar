"""
Sign up, sign in and sign out.

These routes stay thin. Pydantic checks the input, the service does the work and
we set or clear the session cookie. No business logic lives here.
"""

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.auth import LoginIn, RegisterIn, UserOut
from app.services import auth as auth_service
from app.services.demo import create_demo_user
from app.store import Store, get_store

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterIn,
    response: Response,
    db: AsyncSession = Depends(get_db),
    store: Store = Depends(get_store),
) -> UserOut:
    """
    Make a new account and sign in.
    Answers 409 if the email is already taken.
    """
    user, token = await auth_service.register(db, store, body.email, body.password)
    auth_service.set_session_cookie(response, token)
    return UserOut.model_validate(user)


@router.post("/login", response_model=UserOut, status_code=status.HTTP_200_OK)
async def login(
    body: LoginIn,
    response: Response,
    db: AsyncSession = Depends(get_db),
    store: Store = Depends(get_store),
) -> UserOut:
    """
    Check the email and password and sign in.
    Wrong email and wrong password get the exact same 401 message on purpose.
    """
    user, token = await auth_service.login(db, store, body.email, body.password)
    auth_service.set_session_cookie(response, token)
    return UserOut.model_validate(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    session: str | None = Cookie(default=None),
    _user: User = Depends(get_current_user),  # 401 if nobody is signed in
    store: Store = Depends(get_store),
) -> None:
    """End the session right away and clear the cookie."""
    if session:
        await auth_service.logout(store, session)
    auth_service.clear_session_cookie(response)


@router.post("/demo", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def demo_login(
    request: Request,
    response: Response,
    x_forwarded_for: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
    store: Store = Depends(get_store),
) -> UserOut:
    """
    Try the demo makes a private demo account with sample data and signs into it.
    Answers 404 DEMO_DISABLED when DEMO_ENABLED is false and 429 after 10 per IP an hour.
    """
    if not get_settings().demo_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "Demo accounts are turned off.", "code": "DEMO_DISABLED"},
        )
    peer = request.client.host if request.client else None
    user, token = await create_demo_user(db, store, x_forwarded_for, peer)
    auth_service.set_session_cookie(response, token)
    return UserOut.model_validate(user)


@router.post("/guest", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def guest_login(
    request: Request,
    response: Response,
    x_forwarded_for: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
    store: Store = Depends(get_store),
) -> UserOut:
    """
    Use CoopRadar without signing up. Makes an empty temporary account that lasts 7 days.
    You can keep it for good later with POST /api/me/claim.
    """
    if not get_settings().demo_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "Guest accounts are turned off.", "code": "DEMO_DISABLED"},
        )
    peer = request.client.host if request.client else None
    user, token = await create_demo_user(db, store, x_forwarded_for, peer, prefill=False)
    auth_service.set_session_cookie(response, token)
    return UserOut.model_validate(user)
