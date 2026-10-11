"""
Account management router — GET /me, PATCH /me/password, DELETE /me.

All routes require authentication via get_current_user dependency.
"""

import redis.asyncio as aioredis
from fastapi import APIRouter, Cookie, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import get_current_user
from app.models.user import User
from app.redis import get_redis
from app.schemas.auth import ChangePasswordIn, DeleteAccountIn, RegisterIn, UserOut
from app.services import auth as auth_service
from app.services.demo import claim_account

router = APIRouter(prefix="/me", tags=["account"])


@router.get("", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)) -> UserOut:
    """Return the currently authenticated user's profile."""
    return UserOut.model_validate(current_user)


@router.patch("/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: ChangePasswordIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Change the user's password.
    Returns 401 if current_password is wrong, 422 if new_password < 10 chars.
    """
    await auth_service.change_password(
        db, current_user, body.current_password, body.new_password
    )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    body: DeleteAccountIn,
    response: Response,
    session: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    redis: aioredis.Redis = Depends(get_redis),
) -> None:
    """
    Permanently delete the account and all associated data (saved postings, statuses).
    CASCADE delete in the DB handles the cascade.  Returns 401 if password is wrong.
    """
    await auth_service.delete_account(
        db, redis, current_user, session or "", body.password
    )
    auth_service.clear_session_cookie(response)


@router.post("/claim", response_model=UserOut)
async def claim(
    body: RegisterIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserOut:
    """
    Keep a temporary (guest/demo) account: add an email + password. All saved jobs, the resume,
    and matches stay. 400 ALREADY_CLAIMED for normal accounts, 409 EMAIL_TAKEN if in use.
    """
    return UserOut.model_validate(await claim_account(db, current_user, body.email, body.password))
