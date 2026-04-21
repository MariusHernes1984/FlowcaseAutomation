"""Agent entity — an admin-configurable chatbot personality + tool set."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


# Literal list of Flowcase MCP tool names. Matches the names exposed by
# the MCP server; keep in sync when new tools are added there.
FlowcaseToolName = Literal[
    "flowcase_list_offices",
    "flowcase_search_users",
    "flowcase_find_user",
    "flowcase_get_cv",
    "flowcase_list_skills",
    "flowcase_find_users_by_skill",
    "flowcase_get_availability",
    "flowcase_list_regions",
]


class Agent(BaseModel):
    """Full agent record as stored in Cosmos (partition key = /id)."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    description: str
    system_prompt: str
    model: str = Field(
        default="gpt-4.1",
        description="Azure OpenAI deployment name.",
    )
    allowed_tools: list[str] = Field(
        default_factory=list,
        description=(
            "Subset of MCP tool names this agent may call. Empty list "
            "means no tools; use ['*'] to allow every tool the server "
            "exposes at call time."
        ),
    )
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1, le=32768)
    is_active: bool = True
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class AgentCreate(BaseModel):
    id: str | None = None  # server generates if omitted
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(max_length=500)
    system_prompt: str = Field(min_length=1)
    model: str = "gpt-4.1"
    allowed_tools: list[str] = Field(default_factory=lambda: ["*"])
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int | None = None


class AgentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    system_prompt: str | None = None
    model: str | None = None
    allowed_tools: list[str] | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = None
    is_active: bool | None = None
