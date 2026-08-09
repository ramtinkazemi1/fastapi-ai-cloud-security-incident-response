"""Authentication and user-management contracts."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UserRole(StrEnum):
    """Small role set used by the resume-project workflow."""

    ANALYST = "analyst"
    ADMIN = "admin"


class UserCreate(BaseModel):
    """Credentials accepted when an administrator creates a user."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=12, max_length=128)
    role: UserRole = UserRole.ANALYST


class UserRead(BaseModel):
    """Safe user representation that never includes password data."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    role: UserRole
    created_at: datetime


class LoginRequest(BaseModel):
    """Username and password exchanged for a short-lived token."""

    username: str
    password: str


class TokenResponse(BaseModel):
    """Bearer token returned after successful authentication."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
