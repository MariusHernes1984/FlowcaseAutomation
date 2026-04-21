"""Chat orchestration: message → LLM → tool-call loop → final assistant turn.

Emits SSE events as the conversation unfolds:

* ``text_delta``   — streaming assistant text
* ``tool_call``    — LLM decided to call an MCP tool (name + parsed args)
* ``tool_result``  — MCP tool returned (truncated preview)
* ``done``         — full turn complete (chat_id, final text, tool_count)
* ``error``        — fatal error within the turn

Each event is rendered as ``event: <name>\\ndata: <json>\\n\\n`` for
browsers' native ``EventSource`` support.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

from flowcase_web.config import Settings
from flowcase_web.llm import build_openai_client, mcp_tools_to_openai_schema
from flowcase_web.mcp_client import FlowcaseMcpClient
from flowcase_web.models import Agent, ChatMessage, ChatSession

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 8
TOOL_RESULT_PREVIEW_CHARS = 4000


def _sse(event: str, data: Any) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_openai_messages(
    system_prompt: str, history: list[ChatMessage]
) -> list[dict[str, Any]]:
    """Translate our ChatMessage objects to the OpenAI message shape."""
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt}
    ]
    for m in history:
        if m.role == "user":
            messages.append({"role": "user", "content": m.content})
        elif m.role == "assistant":
            msg: dict[str, Any] = {"role": "assistant", "content": m.content or None}
            if m.tool_calls:
                msg["tool_calls"] = m.tool_calls
            messages.append(msg)
        elif m.role == "tool":
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": m.tool_call_id or "",
                    "name": m.name or "",
                    "content": m.content,
                }
            )
        elif m.role == "system":
            # Additional system messages already included via the prompt.
            continue
    return messages


async def run_turn(
    *,
    session: ChatSession,
    agent: Agent,
    user_content: str,
    settings: Settings,
) -> AsyncIterator[str]:
    """Drive a full turn: user message → assistant answer. Yields SSE chunks.

    Mutates ``session.messages`` in place — caller should persist after.
    """
    try:
        llm = build_openai_client(settings)
        mcp = FlowcaseMcpClient(settings.mcp_url, settings.mcp_api_key)
    except Exception as exc:
        yield _sse("error", {"message": f"config error: {exc}"})
        return

    # Append the new user turn before driving the loop.
    session.messages.append(ChatMessage(role="user", content=user_content))

    # Build a tool schema restricted to this agent's allowed tools.
    try:
        mcp_tools = await mcp.list_tools()
    except Exception as exc:
        logger.exception("mcp list_tools failed")
        yield _sse("error", {"message": f"MCP unreachable: {exc}"})
        return
    openai_tools = mcp_tools_to_openai_schema(
        mcp_tools, allowed=agent.allowed_tools or []
    )

    final_text: str = ""
    tool_rounds = 0

    while True:
        openai_messages = _as_openai_messages(agent.system_prompt, session.messages)
        kwargs: dict[str, Any] = {
            "model": agent.model,
            "messages": openai_messages,
            "stream": True,
            "temperature": agent.temperature,
        }
        if agent.max_tokens is not None:
            kwargs["max_tokens"] = agent.max_tokens
        if openai_tools:
            kwargs["tools"] = openai_tools
            kwargs["tool_choice"] = "auto"

        text_buffer = ""
        # tool_call accumulators keyed by index (OpenAI streams them partially)
        pending_tool_calls: dict[int, dict[str, Any]] = {}

        try:
            stream = await llm.chat.completions.create(**kwargs)
        except Exception as exc:
            logger.exception("LLM create failed")
            yield _sse("error", {"message": f"LLM error: {exc}"})
            return

        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta is None:
                continue

            if delta.content:
                text_buffer += delta.content
                yield _sse("text_delta", {"content": delta.content})

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    slot = pending_tool_calls.setdefault(
                        idx,
                        {
                            "id": tc.id or "",
                            "type": "function",
                            "function": {"name": "", "arguments": ""},
                        },
                    )
                    if tc.id:
                        slot["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            slot["function"]["name"] += tc.function.name
                        if tc.function.arguments:
                            slot["function"]["arguments"] += tc.function.arguments

        # Decide: did the LLM call tools, or finish cleanly?
        if pending_tool_calls:
            tool_rounds += 1
            assistant_tool_calls = [
                pending_tool_calls[i] for i in sorted(pending_tool_calls)
            ]
            # Record the assistant turn announcing the tool calls.
            session.messages.append(
                ChatMessage(
                    role="assistant",
                    content=text_buffer,
                    tool_calls=assistant_tool_calls,
                )
            )

            for tc in assistant_tool_calls:
                name = tc["function"]["name"]
                raw_args = tc["function"]["arguments"] or "{}"
                try:
                    arguments = json.loads(raw_args)
                except json.JSONDecodeError as exc:
                    err = f"invalid arguments JSON for {name}: {exc}"
                    yield _sse("error", {"message": err})
                    result_text = err
                else:
                    yield _sse(
                        "tool_call",
                        {"name": name, "arguments": arguments, "id": tc["id"]},
                    )
                    try:
                        result_text = await mcp.call_tool(name, arguments)
                    except Exception as exc:
                        logger.exception("MCP tool %s failed", name)
                        result_text = f"Error: {exc}"

                preview = result_text[:TOOL_RESULT_PREVIEW_CHARS]
                yield _sse(
                    "tool_result",
                    {
                        "name": name,
                        "id": tc["id"],
                        "content": preview,
                        "truncated": len(result_text) > TOOL_RESULT_PREVIEW_CHARS,
                    },
                )

                session.messages.append(
                    ChatMessage(
                        role="tool",
                        tool_call_id=tc["id"],
                        name=name,
                        content=result_text,
                    )
                )

            if tool_rounds >= MAX_TOOL_ROUNDS:
                yield _sse(
                    "error",
                    {"message": f"aborting after {MAX_TOOL_ROUNDS} tool rounds"},
                )
                break
            # Loop again — let the LLM react to the tool output.
            continue

        # No tool calls → this is the final assistant answer.
        final_text = text_buffer
        session.messages.append(ChatMessage(role="assistant", content=final_text))
        break

    session.updated_at = _now()
    if session.title in ("", "New chat"):
        # Use first 64 chars of the opening user message as the title.
        session.title = (user_content or "New chat").strip().splitlines()[0][:64] or "New chat"

    yield _sse(
        "done",
        {
            "chat_id": session.id,
            "title": session.title,
            "tool_rounds": tool_rounds,
            "final_text": final_text,
        },
    )
