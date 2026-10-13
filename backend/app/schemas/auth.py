"""
Shapes for sign up, sign in and account endpoints.

They match the contracts in specs/002-accounts-tracker/contracts/api.md.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterIn(BaseModel):
    """Sign up body. The email has to look real and the password needs 10 or more characters."""
    email: EmailStr
    password: str = Field(min_length=10)


class LoginIn(BaseModel):
    """Sign in body. No length rule here so a wrong password gets 401 and not 422."""
    email: EmailStr
    password: str


class UserOut(BaseModel):
    """The user we send back. Never has hashed_password in it."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    created_at: datetime
    is_admin: bool = False
    is_demo: bool = False


class ChangePasswordIn(BaseModel):
    """Change password body. The new one follows the same rules as sign up."""
    current_password: str
    new_password: str = Field(min_length=10)


class DeleteAccountIn(BaseModel):
    """Delete account body. Asks for the password so nobody deletes by accident."""
    password: str
