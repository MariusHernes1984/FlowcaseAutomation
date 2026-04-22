"""FastAPI dependencies: load the current user from a bearer token."""

from __future__ import annotations

from azure.cosmos import exceptions as cosmos_exc
from fastapi import Depends, HTTPException, Request, status
from jose import JWTError

from flowcase_web.auth import tokens
from flowcase_web.config import Settings, get_settings
from flowcase_web.models import User
from flowcase_web.storage import CosmosHandle, get_handle


def _extract_bearer(request: Request) -> str:
    header = request.headers.get("Authorization") or ""
    parts = header.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return parts[1].strip()


async def get_current_user(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> User:
    token = _extract_bearer(request)
    try:
        payload = tokens.decode(token, settings, expected_kind="access")
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    handle: CosmosHandle = get_handle()
    try:
        doc = await handle.users.read_item(item=payload.sub, partition_key=payload.sub)
    except cosmos_exc.CosmosResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        ) from exc

    user = User.model_validate(doc)
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is deactivated",
        )
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return user
