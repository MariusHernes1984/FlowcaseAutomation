"""Chat session + message models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Role = Literal["user", "assistant", "tool", "system"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ChatMessage(BaseModel):
    role: Role
    content: str = ""
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None
    name: str | None = None  # tool name (for role=tool)
    created_at: datetime = Field(default_factory=_now)


class ChatSession(BaseModel):
    """One conversation. Stored in the 'chats' container, partitioned by userId."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    userId: str  # partition key — camelCase matches Cosmos document shape
    agent_id: str
    title: str = "New chat"
    messages: list[ChatMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class ChatSessionSummary(BaseModel):
    """Trimmed view for listing a user's recent chats."""

    id: str
    agent_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int


class PostMessageRequest(BaseModel):
    content: str = Field(min_length=1)
