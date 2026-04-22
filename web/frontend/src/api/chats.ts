import { api, getAccessToken } from "@/api/client";
import type { ChatSession, ChatSessionSummary } from "@/types";

export async function listChats(): Promise<ChatSessionSummary[]> {
  const r = await api.get<ChatSessionSummary[]>("/chats");
  return r.data;
}

export async function getChat(id: string): Promise<ChatSession> {
  const r = await api.get<ChatSession>(`/chats/${id}`);
  return r.data;
}

export async function deleteChat(id: string): Promise<void> {
  await api.delete(`/chats/${id}`);
}

export type SseHandler = {
  onTextDelta?: (content: string) => void;
  onToolCall?: (info: { id: string; name: string; arguments: unknown }) => void;
  onToolResult?: (info: {
    id: string;
    name: string;
    content: string;
    truncated: boolean;
  }) => void;
  onDone?: (info: {
    chat_id: string;
    title: string;
    tool_rounds: number;
    final_text: string;
  }) => void;
  onError?: (message: string) => void;
};

/**
 * POST a message to an agent and stream back SSE events.
 *
 * Uses fetch (EventSource doesn't support POST). Returns a function that
 * can be called to abort mid-stream.
 */
export function streamChat(
  agentId: string,
  content: string,
  chatId: string | null,
  handlers: SseHandler,
): () => void {
  const controller = new AbortController();
  (async () => {
    const token = getAccessToken();
    try {
      const res = await fetch(`/api/chats/${agentId}/messages`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ content, chat_id: chatId }),
        signal: controller.signal,
        credentials: "include",
      });
      if (!res.ok || !res.body) {
        handlers.onError?.(`HTTP ${res.status}`);
        return;
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const frames = buffer.split("\n\n");
        buffer = frames.pop() ?? "";
        for (const frame of frames) dispatch(frame, handlers);
      }
      if (buffer.trim()) dispatch(buffer, handlers);
    } catch (e) {
      if ((e as Error).name !== "AbortError") {
        handlers.onError?.((e as Error).message);
      }
    }
  })();
  return () => controller.abort();
}

function dispatch(frame: string, h: SseHandler) {
  const lines = frame.split("\n");
  let event = "";
  let data = "";
  for (const line of lines) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) data += line.slice(5).trim();
  }
  if (!event || !data) return;
  let parsed: unknown;
  try {
    parsed = JSON.parse(data);
  } catch {
    return;
  }
  switch (event) {
    case "text_delta":
      h.onTextDelta?.((parsed as { content: string }).content);
      break;
    case "tool_call":
      h.onToolCall?.(
        parsed as { id: string; name: string; arguments: unknown },
      );
      break;
    case "tool_result":
      h.onToolResult?.(
        parsed as {
          id: string;
          name: string;
          content: string;
          truncated: boolean;
        },
      );
      break;
    case "done":
      h.onDone?.(
        parsed as {
          chat_id: string;
          title: string;
          tool_rounds: number;
          final_text: string;
        },
      );
      break;
    case "error":
      h.onError?.((parsed as { message: string }).message);
      break;
  }
}
