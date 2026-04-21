"""Auth endpoints: login, refresh, me, and admin-side user management."""

from __future__ import annotations

import uuid
from typing import Any

from azure.cosmos import exceptions as cosmos_exc
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from jose import JWTError
from pydantic import BaseModel, EmailStr

from flowcase_web.auth import tokens
from flowcase_web.auth.deps import get_current_user, require_admin
from flowcase_web.auth.password import hash_password, verify_password
from flowcase_web.config import Settings, get_settings
from flowcase_web.models import User, UserCreate, UserPublic, UserUpdate
from flowcase_web.storage import CosmosHandle, get_handle

router = APIRouter()

REFRESH_COOKIE_NAME = "flowcase_refresh"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


# ---------------------------------------------------------------------------
# Login / refresh
# ---------------------------------------------------------------------------


def _refresh_cookie_kwargs(settings: Settings) -> dict[str, Any]:
    return {
        "httponly": True,
        "secure": settings.environment != "dev",
        "samesite": "lax",
        "max_age": settings.refresh_token_ttl_days * 24 * 3600,
        "path": "/",
    }


async def _find_user_by_email(handle: CosmosHandle, email: str) -> User | None:
    query = "SELECT TOP 1 * FROM u WHERE LOWER(u.email) = @email"
    params = [{"name": "@email", "value": email.strip().lower()}]
    async for doc in handle.users.query_items(query=query, parameters=params):
        return User.model_validate(doc)
    return None


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    response: Response,
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    handle = get_handle()
    user = await _find_user_by_email(handle, body.email)
    if user is None or not user.is_active or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    access = tokens.encode(user.id, user.role, "access", settings)
    refresh = tokens.encode(user.id, user.role, "refresh", settings)
    response.set_cookie(REFRESH_COOKIE_NAME, refresh, **_refresh_cookie_kwargs(settings))
    return TokenResponse(access_token=access, user=UserPublic.from_user(user))


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    response: Response,
    refresh_cookie: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    if not refresh_cookie:
        raise HTTPException(status_code=401, detail="Missing refresh cookie")
    try:
        payload = tokens.decode(refresh_cookie, settings, expected_kind="refresh")
    except JWTError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid refresh: {exc}") from exc

    handle = get_handle()
    try:
        doc = await handle.users.read_item(item=payload.sub, partition_key=payload.sub)
    except cosmos_exc.CosmosResourceNotFoundError as exc:
        raise HTTPException(status_code=401, detail="User not found") from exc
    user = User.model_validate(doc)
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User deactivated")

    access = tokens.encode(user.id, user.role, "access", settings)
    # Rotate the refresh token too — simple token rotation, no blacklist yet
    refresh = tokens.encode(user.id, user.role, "refresh", settings)
    response.set_cookie(REFRESH_COOKIE_NAME, refresh, **_refresh_cookie_kwargs(settings))
    return TokenResponse(access_token=access, user=UserPublic.from_user(user))


@router.post("/logout")
async def logout(
    response: Response,
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    response.delete_cookie(
        REFRESH_COOKIE_NAME, path="/", secure=settings.environment != "dev"
    )
    return {"status": "ok"}


@router.get("/me", response_model=UserPublic)
async def me(user: User = Depends(get_current_user)) -> UserPublic:
    return UserPublic.from_user(user)


# ---------------------------------------------------------------------------
# Admin-only user management (list, create, update, deactivate)
# ---------------------------------------------------------------------------


@router.get("/users", response_model=list[UserPublic])
async def list_users(_admin: User = Depends(require_admin)) -> list[UserPublic]:
    handle = get_handle()
    out: list[UserPublic] = []
    async for doc in handle.users.query_items(query="SELECT * FROM u"):
        out.append(UserPublic.from_user(User.model_validate(doc)))
    return out


@router.post(
    "/users",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    body: UserCreate, _admin: User = Depends(require_admin)
) -> UserPublic:
    handle = get_handle()
    existing = await _find_user_by_email(handle, body.email)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email {body.email} already exists",
        )
    user = User(
        id=str(uuid.uuid4()),
        email=body.email,
        name=body.name,
        password_hash=hash_password(body.password),
        role=body.role,
    )
    await handle.users.create_item(body=user.model_dump(mode="json"))
    return UserPublic.from_user(user)


@router.patch("/users/{user_id}", response_model=UserPublic)
async def update_user(
    user_id: str,
    body: UserUpdate,
    _admin: User = Depends(require_admin),
) -> UserPublic:
    handle = get_handle()
    try:
        doc = await handle.users.read_item(item=user_id, partition_key=user_id)
    except cosmos_exc.CosmosResourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="User not found") from exc

    user = User.model_validate(doc)
    data = body.model_dump(exclude_unset=True)
    if "password" in data:
        user.password_hash = hash_password(data.pop("password"))
    for k, v in data.items():
        setattr(user, k, v)
    from datetime import datetime, timezone

    user.updated_at = datetime.now(timezone.utc)
    await handle.users.replace_item(item=user.id, body=user.model_dump(mode="json"))
    return UserPublic.from_user(user)
