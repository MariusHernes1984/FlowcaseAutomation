"""Thin wrapper around the Azure Cosmos SQL client.

Exposes the three containers the web app uses (``users``, ``agents``,
``chats``). Initialized once on app startup, reused per-request.

Design notes:

* All three containers are partitioned by a single field — ``/id`` for
  users and agents, ``/userId`` for chats — to make point reads cheap.
* Container creation is NOT done here (Bicep handles it). If the Cosmos
  account doesn't yet have the database/containers, provisioning must
  happen in infra, not at runtime.
* For prod we'll switch from master-key auth to managed identity +
  RBAC via ``DefaultAzureCredential``. Both paths are supported below:
  a non-empty ``cosmos_key`` takes the key path; otherwise identity.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from azure.cosmos.aio import ContainerProxy, CosmosClient, DatabaseProxy
from azure.identity.aio import DefaultAzureCredential

from flowcase_web.config import Settings

logger = logging.getLogger(__name__)


@dataclass
class CosmosHandle:
    client: CosmosClient
    database: DatabaseProxy
    users: ContainerProxy
    agents: ContainerProxy
    chats: ContainerProxy
    evaluations: ContainerProxy


_handle: CosmosHandle | None = None


async def connect(settings: Settings) -> CosmosHandle:
    """Build a Cosmos handle once per process. Idempotent."""
    global _handle
    if _handle is not None:
        return _handle

    if settings.cosmos_key:
        client = CosmosClient(settings.cosmos_endpoint, credential=settings.cosmos_key)
    else:
        # Managed identity / az-cli login — requires Cosmos DB Built-in
        # Data Contributor role on the target account.
        credential = DefaultAzureCredential()
        client = CosmosClient(settings.cosmos_endpoint, credential=credential)

    db = client.get_database_client(settings.cosmos_database)
    handle = CosmosHandle(
        client=client,
        database=db,
        users=db.get_container_client(settings.cosmos_container_users),
        agents=db.get_container_client(settings.cosmos_container_agents),
        chats=db.get_container_client(settings.cosmos_container_chats),
        evaluations=db.get_container_client(settings.cosmos_container_evaluations),
    )
    _handle = handle
    logger.info("Cosmos connected to %s / %s", settings.cosmos_endpoint, settings.cosmos_database)
    return handle


async def close() -> None:
    global _handle
    if _handle is not None:
        await _handle.client.close()
        _handle = None


def get_handle() -> CosmosHandle:
    """Access the singleton — raises if connect() wasn't called."""
    if _handle is None:
        raise RuntimeError("Cosmos not initialized. Call connect() during app startup.")
    return _handle
