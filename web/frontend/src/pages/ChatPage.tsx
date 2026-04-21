import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { listAgents } from "@/api/agents";
import { getChat, listChats, streamChat } from "@/api/chats";
import { renderToolResult } from "@/components/tool-results";
import { Badge, Button, Card, Textarea } from "@/components/ui";
import type { Agent, ChatMessage, ChatSessionSummary } from "@/types";

interface ChatView {
  id: string | null;
  agentId: string;
  messages: ChatMessage[];
  streaming: boolean;
  toolEvents: ToolEvent[];
}

interface ToolEvent {
  id: string;
  name: string;
  arguments?: unknown;
  content?: string;
  truncated?: boolean;
  state: "calling" | "done";
}

export default function ChatPage() {
  const qc = useQueryClient();
  const agentsQuery = useQuery({ queryKey: ["agents"], queryFn: listAgents });
  const chatsQuery = useQuery({ queryKey: ["chats"], queryFn: listChats });

  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [view, setView] = useState<ChatView | null>(null);
  const [input, setInput] = useState("");
  const abortRef = useRef<(() => void) | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const agents = agentsQuery.data ?? [];
  const chats = chatsQuery.data ?? [];

  // Auto-select first agent
  useEffect(() => {
    if (!selectedAgentId && agents.length > 0) {
      setSelectedAgentId(agents[0].id);
    }
  }, [agents, selectedAgentId]);

  // Auto-scroll to latest message
  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [view?.messages.length, view?.toolEvents.length]);

  const openChat = useCallback(async (summary: ChatSessionSummary) => {
    const chat = await getChat(summary.id);
    setSelectedAgentId(chat.agent_id);
    setView({
      id: chat.id,
      agentId: chat.agent_id,
      messages: chat.messages,
      streaming: false,
      toolEvents: [],
    });
  }, []);

  const startNewChat = useCallback(() => {
    abortRef.current?.();
    abortRef.current = null;
    setView(null);
  }, []);

  const send = useCallback(
    (agentId: string, content: string) => {
      setView((prev) => ({
        id: prev?.id ?? null,
        agentId,
        messages: [
          ...(prev?.messages ?? []),
          {
            role: "user",
            content,
            created_at: new Date().toISOString(),
          },
          {
            role: "assistant",
            content: "",
            created_at: new Date().toISOString(),
          },
        ],
        streaming: true,
        toolEvents: prev?.toolEvents ?? [],
      }));

      abortRef.current = streamChat(
        agentId,
        content,
        view?.id ?? null,
        {
          onTextDelta: (chunk) => {
            setView((prev) => {
              if (!prev) return prev;
              const msgs = [...prev.messages];
              const last = msgs[msgs.length - 1];
              if (last && last.role === "assistant") {
                msgs[msgs.length - 1] = {
                  ...last,
                  content: last.content + chunk,
                };
              }
              return { ...prev, messages: msgs };
            });
          },
          onToolCall: (info) => {
            setView((prev) => {
              if (!prev) return prev;
              return {
                ...prev,
                toolEvents: [
                  ...prev.toolEvents,
                  {
                    id: info.id,
                    name: info.name,
                    arguments: info.arguments,
                    state: "calling",
                  },
                ],
              };
            });
          },
          onToolResult: (info) => {
            setView((prev) => {
              if (!prev) return prev;
              return {
                ...prev,
                toolEvents: prev.toolEvents.map((ev) =>
                  ev.id === info.id
                    ? {
                        ...ev,
                        state: "done",
                        content: info.content,
                        truncated: info.truncated,
                      }
                    : ev,
                ),
              };
            });
          },
          onDone: (info) => {
            setView((prev) =>
              prev
                ? { ...prev, id: info.chat_id, streaming: false }
                : prev,
            );
            qc.invalidateQueries({ queryKey: ["chats"] });
          },
          onError: (message) => {
            setView((prev) => {
              if (!prev) return prev;
              const msgs = [...prev.messages];
              const last = msgs[msgs.length - 1];
              if (last && last.role === "assistant") {
                msgs[msgs.length - 1] = {
                  ...last,
                  content:
                    (last.content ? last.content + "\n\n" : "") +
                    `⚠️ ${message}`,
                };
              }
              return { ...prev, messages: msgs, streaming: false };
            });
          },
        },
      );
    },
    [qc, view?.id],
  );

  const handleSubmit = () => {
    const trimmed = input.trim();
    if (!trimmed || !selectedAgentId) return;
    if (view?.streaming) return;
    setInput("");
    send(selectedAgentId, trimmed);
  };

  const selectedAgent = useMemo(
    () => agents.find((a) => a.id === selectedAgentId) ?? null,
    [agents, selectedAgentId],
  );

  return (
    <div className="flex h-full min-h-0 flex-1">
      <ChatSidebar
        agents={agents}
        chats={chats}
        selectedAgentId={selectedAgentId}
        activeChatId={view?.id ?? null}
        onSelectAgent={(id) => {
          setSelectedAgentId(id);
          setView(null);
        }}
        onOpenChat={openChat}
        onNewChat={startNewChat}
      />

      <div className="flex flex-1 flex-col">
        {selectedAgent && (
          <div className="border-b border-slate-200 bg-white px-6 py-3">
            <div className="flex items-baseline gap-3">
              <h2 className="text-lg font-semibold">{selectedAgent.name}</h2>
              <Badge>{selectedAgent.model}</Badge>
            </div>
            <p className="mt-1 text-sm text-slate-500">
              {selectedAgent.description}
            </p>
          </div>
        )}

        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto px-6 py-6 space-y-4"
        >
          {view?.messages.map((m, i) => (
            <Message key={`m-${i}`} message={m} />
          ))}
          {view?.toolEvents.length ? (
            <div className="space-y-2">
              {view.toolEvents.map((ev) => (
                <ToolBlock key={`t-${ev.id}`} event={ev} />
              ))}
            </div>
          ) : null}
          {!view && (
            <div className="mx-auto mt-20 max-w-md text-center text-sm text-slate-500">
              Start en ny samtale med <b>{selectedAgent?.name ?? "en agent"}</b>{" "}
              ved å skrive under.
            </div>
          )}
        </div>

        <div className="border-t border-slate-200 bg-white p-4">
          <div className="mx-auto flex max-w-4xl gap-3">
            <Textarea
              rows={2}
              placeholder="Skriv en melding… (Enter for å sende, Shift+Enter for ny linje)"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit();
                }
              }}
              disabled={view?.streaming}
            />
            <Button onClick={handleSubmit} disabled={view?.streaming || !input.trim()}>
              {view?.streaming ? "…" : "Send"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

function ChatSidebar({
  agents,
  chats,
  selectedAgentId,
  activeChatId,
  onSelectAgent,
  onOpenChat,
  onNewChat,
}: {
  agents: Agent[];
  chats: ChatSessionSummary[];
  selectedAgentId: string | null;
  activeChatId: string | null;
  onSelectAgent: (id: string) => void;
  onOpenChat: (c: ChatSessionSummary) => void;
  onNewChat: () => void;
}) {
  return (
    <aside className="flex w-72 flex-col border-r border-slate-200 bg-slate-50">
      <div className="border-b border-slate-200 p-3">
        <Button onClick={onNewChat} className="w-full" size="sm">
          + Ny samtale
        </Button>
      </div>
      <div className="border-b border-slate-200 p-3">
        <div className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">
          Agenter
        </div>
        <div className="space-y-1">
          {agents.map((a) => (
            <button
              key={a.id}
              onClick={() => onSelectAgent(a.id)}
              className={`w-full rounded-md px-3 py-2 text-left text-sm transition ${
                selectedAgentId === a.id
                  ? "bg-slate-900 text-white"
                  : "hover:bg-slate-200"
              }`}
            >
              <div className="font-medium">{a.name}</div>
              <div className="text-xs opacity-70">{a.description}</div>
            </button>
          ))}
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-3">
        <div className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">
          Tidligere samtaler
        </div>
        <div className="space-y-1">
          {chats.map((c) => (
            <button
              key={c.id}
              onClick={() => onOpenChat(c)}
              className={`w-full truncate rounded-md px-3 py-2 text-left text-sm ${
                activeChatId === c.id
                  ? "bg-slate-200"
                  : "hover:bg-slate-100"
              }`}
            >
              <div className="truncate font-medium">{c.title}</div>
              <div className="text-xs text-slate-500">
                {new Date(c.updated_at).toLocaleString()} · {c.message_count} msg
              </div>
            </button>
          ))}
          {chats.length === 0 && (
            <div className="text-xs text-slate-500">Ingen samtaler ennå.</div>
          )}
        </div>
      </div>
    </aside>
  );
}

function Message({ message }: { message: ChatMessage }) {
  if (message.role === "tool" || message.role === "system") return null;
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] whitespace-pre-wrap rounded-lg px-4 py-3 text-sm ${
          isUser
            ? "bg-slate-900 text-white"
            : "border border-slate-200 bg-white text-slate-900"
        }`}
      >
        {message.content || (isUser ? "" : "…")}
      </div>
    </div>
  );
}

function ToolBlock({ event }: { event: ToolEvent }) {
  return (
    <Card className="border-slate-200 bg-slate-50 p-3 text-xs">
      <div className="flex items-center gap-2 font-mono text-slate-700">
        <span>🛠️</span>
        <span className="font-semibold">{event.name}</span>
        <Badge tone={event.state === "done" ? "green" : "amber"}>
          {event.state === "done" ? "ferdig" : "kjører…"}
        </Badge>
        {event.truncated && <Badge tone="amber">trunkert</Badge>}
      </div>

      {event.content && (
        <div className="mt-3">{renderToolResult(event.name, event.content)}</div>
      )}

      {event.arguments !== undefined && (
        <details className="mt-2 text-slate-700">
          <summary className="cursor-pointer select-none text-[11px] text-slate-500">
            Argumenter
          </summary>
          <pre className="mt-1 overflow-x-auto rounded bg-white p-2 text-[11px] text-slate-600">
            {JSON.stringify(event.arguments, null, 2)}
          </pre>
        </details>
      )}

      {event.content && (
        <details className="mt-1 text-slate-700">
          <summary className="cursor-pointer select-none text-[11px] text-slate-500">
            Rå JSON
          </summary>
          <pre className="mt-1 max-h-64 overflow-auto rounded bg-white p-2 text-[11px] text-slate-700">
            {event.content}
          </pre>
        </details>
      )}
    </Card>
  );
}
