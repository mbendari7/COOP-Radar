"""
Your account. GET /me, PATCH /me/password and DELETE /me.

Every route here needs you to be signed in.
"""

from fastapi import APIRouter, Cookie, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.auth import ChangePasswordIn, DeleteAccountIn, RegisterIn, UserOut
from app.services import auth as auth_service
from app.services.demo import claim_account
from app.store import Store, get_store

router = APIRouter(prefix="/me", tags=["account"])


@router.get("", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)) -> UserOut:
    """Give back the signed in person's profile."""
    return UserOut.model_validate(current_user)


@router.patch("/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: ChangePasswordIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Change your password.
    Answers 401 if the current password is wrong and 422 if the new one is under 10 characters.
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
    store: Store = Depends(get_store),
) -> None:
    """
    Delete the account and everything tied to it for good, like saved jobs and statuses.
    The database cascade does the cleanup. Answers 401 if the password is wrong.
    """
    await auth_service.delete_account(
        db, store, current_user, session or "", body.password
    )
    auth_service.clear_session_cookie(response)


@router.post("/claim", response_model=UserOut)
async def claim(
    body: RegisterIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserOut:
    """
    Keep a temporary or demo account by adding an email and password. Saved jobs, the resume
    and matches all stay. 400 ALREADY_CLAIMED for normal accounts and 409 EMAIL_TAKEN if in use.
    """
    return UserOut.model_validate(await claim_account(db, current_user, body.email, body.password))
