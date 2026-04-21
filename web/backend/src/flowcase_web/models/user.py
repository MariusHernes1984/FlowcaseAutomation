"""User entity stored in Cosmos."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

Role = Literal["admin", "user"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(BaseModel):
    """Full user record as stored in Cosmos (partition key = /id)."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    email: EmailStr
    name: str
    password_hash: str
    role: Role = "user"
    is_active: bool = True
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class UserPublic(BaseModel):
    """Response model — never includes password_hash."""

    id: str
    email: EmailStr
    name: str
    role: Role
    is_active: bool
    created_at: datetime

    @classmethod
    def from_user(cls, u: User) -> "UserPublic":
        return cls(
            id=u.id,
            email=u.email,
            name=u.name,
            role=u.role,
            is_active=u.is_active,
            created_at=u.created_at,
        )


class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str = Field(min_length=8, max_length=256)
    role: Role = "user"


class UserUpdate(BaseModel):
    name: str | None = None
    password: str | None = Field(default=None, min_length=8, max_length=256)
    role: Role | None = None
    is_active: bool | None = None
