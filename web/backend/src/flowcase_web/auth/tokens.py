"""JWT access-token + refresh-token helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal

from jose import JWTError, jwt
from pydantic import BaseModel

from flowcase_web.config import Settings

TokenKind = Literal["access", "refresh"]


class TokenPayload(BaseModel):
    sub: str  # user id
    kind: TokenKind
    role: str
    exp: datetime
    iat: datetime


def _now() -> datetime:
    return datetime.now(timezone.utc)


def encode(
    user_id: str,
    role: str,
    kind: TokenKind,
    settings: Settings,
) -> str:
    now = _now()
    if kind == "access":
        exp = now + timedelta(minutes=settings.access_token_ttl_minutes)
    else:
        exp = now + timedelta(days=settings.refresh_token_ttl_days)
    payload = {
        "sub": user_id,
        "role": role,
        "kind": kind,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode(token: str, settings: Settings, *, expected_kind: TokenKind) -> TokenPayload:
    """Decode and validate a token. Raises ``JWTError`` on failure."""
    data = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if data.get("kind") != expected_kind:
        raise JWTError(f"Expected {expected_kind} token, got {data.get('kind')!r}")
    return TokenPayload(
        sub=data["sub"],
        kind=data["kind"],
        role=data.get("role", "user"),
        exp=datetime.fromtimestamp(data["exp"], tz=timezone.utc),
        iat=datetime.fromtimestamp(data["iat"], tz=timezone.utc),
    )
