"""Cosmos DB client wrappers."""

from flowcase_web.storage.cosmos import CosmosHandle, close, connect, get_handle

__all__ = ["CosmosHandle", "close", "connect", "get_handle"]
