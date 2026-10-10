"""
Pydantic schemas for authentication endpoints.

Shapes match the API contracts in specs/002-accounts-tracker/contracts/api.md.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterIn(BaseModel):
    """Registration payload — email must be valid format, password ≥ 10 chars."""
    email: EmailStr
    password: str = Field(min_length=10)


class LoginIn(BaseModel):
    """Login payload — password has no min length here (wrong pw → 401, not 422)."""
    email: EmailStr
    password: str


class UserOut(BaseModel):
    """Public user representation — never includes hashed_password."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    created_at: datetime
    is_admin: bool = False


class ChangePasswordIn(BaseModel):
    """Password change payload — new password must meet the same rules as registration."""
    current_password: str
    new_password: str = Field(min_length=10)


class DeleteAccountIn(BaseModel):
    """Account deletion — requires password confirmation to prevent accidental deletion."""
    password: str
