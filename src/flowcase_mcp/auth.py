"""API key authentication middleware for the streamable HTTP transport.

stdio deployments don't need this — the stdio MCP is a subprocess of the
client and inherits its trust boundary. The streamable HTTP variant is
exposed over the network, so every request has to be authenticated.

Strategy: a single shared secret ``FLOWCASE_MCP_API_KEY`` checked in a
Starlette middleware. Good enough for single-user Azure Container App
deployments. Swap to Entra ID / OAuth once more than one person needs
access.
"""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable
from typing import Iterable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

DEFAULT_HEADER_NAME = "X-API-Key"


class ApiKeyAuthMiddleware(BaseHTTPMiddleware):
    """Reject requests that don't carry the expected API key header."""

    def __init__(
        self,
        app,
        *,
        expected_key: str,
        header_name: str = DEFAULT_HEADER_NAME,
        skip_paths: Iterable[str] = (),
    ) -> None:
        super().__init__(app)
        self._expected = expected_key
        self._header = header_name
        self._skip = set(skip_paths)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.url.path in self._skip:
            return await call_next(request)
        key = request.headers.get(self._header)
        if not key:
            return JSONResponse(
                {"error": "missing_api_key", "header": self._header},
                status_code=401,
            )
        if key != self._expected:
            return JSONResponse(
                {"error": "invalid_api_key"}, status_code=403
            )
        return await call_next(request)


def get_api_key_from_env() -> str:
    """Read the MCP API key from env. Fail clearly if unset."""
    key = os.environ.get("FLOWCASE_MCP_API_KEY")
    if not key:
        raise RuntimeError(
            "FLOWCASE_MCP_API_KEY is not set but transport=streamable-http "
            "requires it. Generate a long random string and store it in "
            "Azure Key Vault (or your local .env for testing)."
        )
    return key
