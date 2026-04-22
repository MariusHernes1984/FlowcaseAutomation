"""Chat endpoints (per-user, partitioned by userId in Cosmos)."""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from azure.cosmos import exceptions as cosmos_exc
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from flowcase_web.auth.deps import get_current_user
from flowcase_web.chats.orchestrator import run_turn
from flowcase_web.config import Settings, get_settings
from flowcase_web.models import (
    Agent,
    ChatMessage,
    ChatSession,
    ChatSessionSummary,
    User,
)
from flowcase_web.storage import get_handle

logger = logging.getLogger(__name__)

router = APIRouter()


class NewMessageBody(BaseModel):
    content: str = Field(min_length=1)
    chat_id: str | None = Field(
        default=None,
        description=(
            "Omit on first message to start a new chat. Pass the id "
            "returned from the 'done' event to continue an existing chat."
        ),
    )


# ---------------------------------------------------------------------------
# list / read / delete
# ---------------------------------------------------------------------------


@router.get("", response_model=list[ChatSessionSummary])
async def list_chats(user: User = Depends(get_current_user)) -> list[ChatSessionSummary]:
    handle = get_handle()
    out: list[ChatSessionSummary] = []
    query = (
        "SELECT * FROM c WHERE c.userId = @uid ORDER BY c.updated_at DESC"
    )
    params = [{"name": "@uid", "value": user.id}]
    async for doc in handle.chats.query_items(
        query=query, parameters=params, partition_key=user.id
    ):
        chat = ChatSession.model_validate(doc)
        out.append(
            ChatSessionSummary(
                id=chat.id,
                agent_id=chat.agent_id,
                title=chat.title,
                created_at=chat.created_at,
                updated_at=chat.updated_at,
                message_count=len(chat.messages),
            )
        )
    return out


@router.get("/{chat_id}", response_model=ChatSession)
async def get_chat(chat_id: str, user: User = Depends(get_current_user)) -> ChatSession:
    handle = get_handle()
    try:
        doc = await handle.chats.read_item(item=chat_id, partition_key=user.id)
    except cosmos_exc.CosmosResourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Chat not found") from exc
    return ChatSession.model_validate(doc)


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(chat_id: str, user: User = Depends(get_current_user)) -> None:
    handle = get_handle()
    try:
        await handle.chats.delete_item(item=chat_id, partition_key=user.id)
    except cosmos_exc.CosmosResourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Chat not found") from exc


# ---------------------------------------------------------------------------
# send message — SSE stream
# ---------------------------------------------------------------------------


async def _load_agent(agent_id: str) -> Agent:
    handle = get_handle()
    try:
        doc = await handle.agents.read_item(item=agent_id, partition_key=agent_id)
    except cosmos_exc.CosmosResourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Agent not found") from exc
    agent = Agent.model_validate(doc)
    if not agent.is_active:
        raise HTTPException(status_code=403, detail="Agent is deactivated")
    return agent


async def _load_or_create_chat(
    user: User, agent_id: str, chat_id: str | None
) -> ChatSession:
    handle = get_handle()
    if chat_id:
        try:
            doc = await handle.chats.read_item(item=chat_id, partition_key=user.id)
        except cosmos_exc.CosmosResourceNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Chat not found") from exc
        return ChatSession.model_validate(doc)
    return ChatSession(
        id=str(uuid.uuid4()),
        userId=user.id,
        agent_id=agent_id,
    )


@router.post("/{agent_id}/messages")
async def post_message(
    agent_id: str,
    body: NewMessageBody,
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    agent = await _load_agent(agent_id)
    session = await _load_or_create_chat(user, agent_id, body.chat_id)

    async def stream() -> AsyncIterator[str]:
        async for chunk in run_turn(
            session=session,
            agent=agent,
            user_content=body.content,
            settings=settings,
        ):
            yield chunk
        # Persist after the turn completes.
        handle = get_handle()
        session.updated_at = datetime.now(timezone.utc)
        try:
            await handle.chats.upsert_item(body=session.model_dump(mode="json"))
        except Exception:
            logger.exception("persisting chat %s failed", session.id)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
