"""Agent CRUD endpoints.

Read endpoints are available to any authenticated user (so the chat UI
can list available agents). Write endpoints are admin-only.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from azure.cosmos import exceptions as cosmos_exc
from fastapi import APIRouter, Depends, HTTPException, status

from flowcase_web.auth.deps import get_current_user, require_admin
from flowcase_web.models import Agent, AgentCreate, AgentUpdate, User
from flowcase_web.storage import get_handle

router = APIRouter()

_SLUG_RE = re.compile(r"[^a-z0-9-]+")


def _slugify(name: str) -> str:
    s = name.strip().lower().replace(" ", "-")
    s = _SLUG_RE.sub("", s)
    return s or str(uuid.uuid4())


@router.get("", response_model=list[Agent])
async def list_agents(_user: User = Depends(get_current_user)) -> list[Agent]:
    handle = get_handle()
    out: list[Agent] = []
    async for doc in handle.agents.query_items(query="SELECT * FROM a"):
        out.append(Agent.model_validate(doc))
    return out


@router.get("/{agent_id}", response_model=Agent)
async def get_agent(
    agent_id: str, _user: User = Depends(get_current_user)
) -> Agent:
    handle = get_handle()
    try:
        doc = await handle.agents.read_item(item=agent_id, partition_key=agent_id)
    except cosmos_exc.CosmosResourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Agent not found") from exc
    return Agent.model_validate(doc)


@router.post("", response_model=Agent, status_code=status.HTTP_201_CREATED)
async def create_agent(
    body: AgentCreate, _admin: User = Depends(require_admin)
) -> Agent:
    handle = get_handle()
    agent_id = body.id or _slugify(body.name)
    # Reject if ID collides
    try:
        await handle.agents.read_item(item=agent_id, partition_key=agent_id)
        raise HTTPException(
            status_code=409, detail=f"Agent '{agent_id}' already exists"
        )
    except cosmos_exc.CosmosResourceNotFoundError:
        pass

    agent = Agent(
        id=agent_id,
        name=body.name,
        description=body.description,
        system_prompt=body.system_prompt,
        model=body.model,
        allowed_tools=body.allowed_tools,
        temperature=body.temperature,
        max_tokens=body.max_tokens,
    )
    await handle.agents.create_item(body=agent.model_dump(mode="json"))
    return agent


@router.patch("/{agent_id}", response_model=Agent)
async def update_agent(
    agent_id: str,
    body: AgentUpdate,
    _admin: User = Depends(require_admin),
) -> Agent:
    handle = get_handle()
    try:
        doc = await handle.agents.read_item(item=agent_id, partition_key=agent_id)
    except cosmos_exc.CosmosResourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Agent not found") from exc

    agent = Agent.model_validate(doc)
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(agent, k, v)
    agent.updated_at = datetime.now(timezone.utc)
    await handle.agents.replace_item(item=agent.id, body=agent.model_dump(mode="json"))
    return agent


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: str, _admin: User = Depends(require_admin)
) -> None:
    handle = get_handle()
    try:
        await handle.agents.delete_item(item=agent_id, partition_key=agent_id)
    except cosmos_exc.CosmosResourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Agent not found") from exc
