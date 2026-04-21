"""Entry point for running the Flowcase MCP server over stdio."""

from __future__ import annotations

from flowcase_mcp.server import mcp


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
