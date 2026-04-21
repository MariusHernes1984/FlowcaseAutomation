"""Thin wrapper around the MCP SDK's streamable-HTTP client.

A new session is opened per call to :func:`FlowcaseMcpClient.call_tool`.
That keeps the server-side streamable_http_manager from accumulating
session state across unrelated requests, at the cost of ~100–300 ms
per call (initialize handshake). For this app the LLM latency dwarfs
that, so we accept the trade-off.

The client also exposes :func:`list_tools` so the orchestrator can build
OpenAI-style tool schemas without hard-coding them.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

logger = logging.getLogger(__name__)


class FlowcaseMcpClient:
    def __init__(self, url: str, api_key: str) -> None:
        if not url:
            raise ValueError("MCP URL is required")
        self._url = url
        self._headers = {"X-API-Key": api_key} if api_key else {}

    @asynccontextmanager
    async def _session(self):
        async with streamablehttp_client(self._url, headers=self._headers) as (
            read,
            write,
            _,
        ):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session

    async def list_tools(self) -> list[dict[str, Any]]:
        """Return the raw MCP tool definitions (name, description, inputSchema)."""
        async with self._session() as session:
            result = await session.list_tools()
            return [
                {
                    "name": t.name,
                    "description": t.description or "",
                    "input_schema": t.inputSchema,
                }
                for t in result.tools
            ]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Invoke a tool and return its text content joined.

        MCP tools return a list of content blocks — we only surface text
        content, dropping image/resource blocks for now. The Flowcase
        tools all respond with a single text payload anyway.
        """
        async with self._session() as session:
            result = await session.call_tool(name, arguments)
            # Concatenate text content from the response blocks.
            chunks: list[str] = []
            for block in result.content or []:
                text = getattr(block, "text", None)
                if isinstance(text, str):
                    chunks.append(text)
            return "\n".join(chunks) if chunks else ""
