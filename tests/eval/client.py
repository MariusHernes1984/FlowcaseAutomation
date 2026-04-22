"""Auth + SSE-consuming HTTP client for the Flowcase web backend."""

from __future__ import annotations

import json
import time
from typing import Any

import httpx

from tests.eval.schema import ToolInvocation, Transcript


async def login(
    http: httpx.AsyncClient, target: str, email: str, password: str
) -> str:
    r = await http.post(
        f"{target}/api/auth/login",
        json={"email": email, "password": password},
    )
    r.raise_for_status()
    return r.json()["access_token"]


async def send_chat(
    http: httpx.AsyncClient,
    target: str,
    token: str,
    agent_id: str,
    content: str,
    *,
    timeout_s: float = 300.0,
) -> Transcript:
    url = f"{target}/api/chats/{agent_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    body = {"content": content}
    start = time.monotonic()

    transcript = Transcript(agent=agent_id, question=content)
    tool_by_id: dict[str, ToolInvocation] = {}

    async with http.stream(
        "POST", url, headers=headers, json=body, timeout=timeout_s
    ) as response:
        response.raise_for_status()
        buffer = ""
        async for chunk in response.aiter_text():
            buffer += chunk
            while "\n\n" in buffer:
                frame, buffer = buffer.split("\n\n", 1)
                _dispatch(frame, transcript, tool_by_id)

    transcript.elapsed_seconds = round(time.monotonic() - start, 2)
    transcript.tool_calls = list(tool_by_id.values())
    return transcript


def _dispatch(
    frame: str,
    transcript: Transcript,
    tool_by_id: dict[str, ToolInvocation],
) -> None:
    event = ""
    data_lines: list[str] = []
    for line in frame.splitlines():
        if line.startswith("event:"):
            event = line[6:].strip()
        elif line.startswith("data:"):
            data_lines.append(line[5:].strip())
    if not event or not data_lines:
        return
    try:
        payload: Any = json.loads("".join(data_lines))
    except json.JSONDecodeError:
        return

    if event == "text_delta":
        transcript.final_text += payload.get("content", "")
    elif event == "tool_call":
        tid = payload.get("id") or payload.get("name") or f"tc-{len(tool_by_id)}"
        tool_by_id[tid] = ToolInvocation(
            name=payload.get("name", ""),
            arguments=payload.get("arguments") or {},
        )
    elif event == "tool_result":
        tid = payload.get("id")
        if tid in tool_by_id:
            tool_by_id[tid].result_preview = payload.get("content", "")[:4000]
            tool_by_id[tid].truncated = bool(payload.get("truncated"))
    elif event == "error":
        transcript.errors.append(str(payload.get("message", "")))
    elif event == "done":
        # final_text may already be populated by streaming, but use done payload
        # as authoritative fallback when present.
        if not transcript.final_text and payload.get("final_text"):
            transcript.final_text = payload["final_text"]
