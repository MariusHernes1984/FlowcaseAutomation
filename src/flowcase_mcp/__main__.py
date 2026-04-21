"""Entry point for the Flowcase MCP server.

Supports two transports controlled by ``FLOWCASE_MCP_TRANSPORT`` env var:

* ``stdio`` (default) — local subprocess mode for Claude Code / Desktop.
* ``streamable-http`` — network mode for Azure Container Apps etc.
  Adds API-key auth middleware and a ``/health`` endpoint suitable for
  liveness probes.
"""

from __future__ import annotations

import os

from flowcase_mcp.server import mcp


def _run_stdio() -> None:
    mcp.run()


def _run_streamable_http() -> None:
    # Imports are deferred so stdio-only deployments don't pay the cost.
    import uvicorn
    from starlette.applications import Starlette
    from starlette.requests import Request
    from starlette.responses import PlainTextResponse
    from starlette.routing import Mount, Route

    from flowcase_mcp.auth import ApiKeyAuthMiddleware, get_api_key_from_env

    api_key = get_api_key_from_env()

    async def healthcheck(_request: Request) -> PlainTextResponse:
        return PlainTextResponse("ok")

    mcp_app = mcp.streamable_http_app()
    app = Starlette(
        routes=[
            Route("/health", healthcheck),
            Mount("/", app=mcp_app),
        ]
    )
    app.add_middleware(
        ApiKeyAuthMiddleware,
        expected_key=api_key,
        skip_paths=["/health"],
    )

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


def main() -> None:
    transport = os.environ.get("FLOWCASE_MCP_TRANSPORT", "stdio").strip().lower()
    if transport == "stdio":
        _run_stdio()
    elif transport in {"streamable-http", "streamable_http", "http"}:
        _run_streamable_http()
    else:
        raise RuntimeError(
            f"Unknown FLOWCASE_MCP_TRANSPORT={transport!r}. "
            "Valid values: stdio, streamable-http."
        )


if __name__ == "__main__":
    main()
