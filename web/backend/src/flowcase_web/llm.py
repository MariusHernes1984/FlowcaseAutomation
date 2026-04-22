"""Azure OpenAI wrapper + MCP → OpenAI tool-schema conversion."""

from __future__ import annotations

import logging
from typing import Any

from openai import AsyncAzureOpenAI

from flowcase_web.config import Settings

logger = logging.getLogger(__name__)


def build_openai_client(settings: Settings) -> AsyncAzureOpenAI:
    if not settings.azure_openai_endpoint or not settings.azure_openai_api_key:
        raise RuntimeError(
            "Azure OpenAI is not configured. Set AZURE_OPENAI_ENDPOINT and "
            "AZURE_OPENAI_API_KEY."
        )
    return AsyncAzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
    )


def mcp_tools_to_openai_schema(
    mcp_tools: list[dict[str, Any]],
    *,
    allowed: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Convert MCP tool descriptions to OpenAI function-calling schema.

    ``allowed`` is a list of tool names (or ``['*']``) — any MCP tool
    outside that list is dropped so agents with a restricted tool set
    don't leak capabilities into the LLM context.
    """
    wildcard = allowed is None or "*" in (allowed or [])
    out: list[dict[str, Any]] = []
    for tool in mcp_tools:
        name = tool.get("name")
        if not name:
            continue
        if not wildcard and name not in (allowed or []):
            continue
        # MCP inputSchema is already JSON-schema; OpenAI wants the same
        # shape under "parameters".
        schema = tool.get("input_schema") or {"type": "object", "properties": {}}
        out.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": tool.get("description") or "",
                    "parameters": schema,
                },
            }
        )
    return out
