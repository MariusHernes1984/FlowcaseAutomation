"""Admin bootstrap — create the first admin user if it doesn't exist."""

from __future__ import annotations

import logging
import uuid

from azure.cosmos import exceptions as cosmos_exc

from flowcase_web.auth.password import hash_password
from flowcase_web.config import Settings
from flowcase_web.models import User
from flowcase_web.storage import CosmosHandle

logger = logging.getLogger(__name__)


async def ensure_admin(handle: CosmosHandle, settings: Settings) -> None:
    """Create the configured admin user on first boot. No-op if already present."""
    email = (settings.admin_email or "").strip().lower()
    if not email or not settings.admin_password:
        logger.warning(
            "ADMIN_EMAIL or ADMIN_PASSWORD not set — skipping admin bootstrap"
        )
        return

    # Check if any user with this email already exists.
    query = "SELECT TOP 1 * FROM u WHERE LOWER(u.email) = @email"
    params = [{"name": "@email", "value": email}]
    async for _ in handle.users.query_items(query=query, parameters=params):
        logger.info("Admin user %s already exists — leaving untouched", email)
        return

    user = User(
        id=str(uuid.uuid4()),
        email=email,
        name="Administrator",
        password_hash=hash_password(settings.admin_password),
        role="admin",
        is_active=True,
    )
    try:
        await handle.users.create_item(body=user.model_dump(mode="json"))
        logger.info("Bootstrapped admin user %s", email)
    except cosmos_exc.CosmosResourceExistsError:
        logger.info("Admin user %s raced with another boot — skipping", email)
