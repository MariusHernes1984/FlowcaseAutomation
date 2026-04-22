"""Password hashing + verification via the bcrypt package directly.

passlib has an ongoing incompatibility with bcrypt >= 4.x, so we skip
it and use bcrypt natively. Bcrypt truncates secrets at 72 bytes — we
let it do so since a correctly-generated bcrypt hash is deterministic
across length as long as the secret < 72 bytes, which covers anything
a human types.
"""

from __future__ import annotations

import bcrypt


def hash_password(raw: str) -> str:
    hashed = bcrypt.hashpw(raw.encode("utf-8"), bcrypt.gensalt(rounds=12))
    return hashed.decode("utf-8")


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(raw.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False
