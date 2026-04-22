"""Thin REST endpoints that expose MCP reference data (industries,
regions, skills, customers) directly to the frontend for filter UIs.

These bypass the LLM-driven chat flow — the SPA wants a dropdown /
autocomplete that loads in milliseconds, not a tool-call roundtrip.
"""

from flowcase_web.reference.router import router

__all__ = ["router"]
