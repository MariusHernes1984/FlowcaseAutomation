"""Reference-data proxy endpoints (industries / customers / skills / regions).

Each handler wraps the equivalent Flowcase MCP tool in a straight HTTP
request → JSON pipe. No conversation state, no LLM — just fast lookup
queries the chat composer's filter chips can pull autocomplete from.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from flowcase_web.auth.deps import get_current_user
from flowcase_web.config import Settings, get_settings
from flowcase_web.mcp_client import FlowcaseMcpClient
from flowcase_web.models import User

logger = logging.getLogger(__name__)

router = APIRouter()


async def _mcp_call(
    settings: Settings, tool: str, params: dict[str, Any]
) -> Any:
    if not settings.mcp_url or not settings.mcp_api_key:
        raise HTTPException(status_code=503, detail="MCP not configured")
    client = FlowcaseMcpClient(settings.mcp_url, settings.mcp_api_key)
    # Force JSON response — the MCP tool returns a text payload with the
    # JSON-serialised body inside. We re-parse it here.
    args = {"params": {**params, "response_format": "json"}}
    try:
        raw = await client.call_tool(tool, args)
    except Exception as exc:
        logger.exception("MCP call %s failed", tool)
        raise HTTPException(status_code=502, detail=f"MCP error: {exc}") from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=502, detail=f"MCP returned non-JSON: {exc}"
        ) from exc


@router.get("/industries")
async def list_industries(
    q: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    _user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> Any:
    return await _mcp_call(settings, "flowcase_list_industries", {"query": q, "limit": limit})


@router.get("/customers")
async def list_customers(
    q: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    _user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> Any:
    return await _mcp_call(settings, "flowcase_list_customers", {"query": q, "limit": limit})


@router.get("/skills")
async def list_skills(
    q: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    _user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> Any:
    return await _mcp_call(settings, "flowcase_list_skills", {"query": q, "limit": limit})


@router.get("/regions")
async def list_regions(
    _user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> Any:
    return await _mcp_call(settings, "flowcase_list_regions", {})


@router.get("/offices")
async def list_offices(
    country_codes: list[str] | None = Query(default=None, alias="country"),
    _user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> Any:
    params: dict[str, Any] = {}
    if country_codes:
        params["country_codes"] = country_codes
    return await _mcp_call(settings, "flowcase_list_offices", params)
