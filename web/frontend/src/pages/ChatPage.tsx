import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bot,
  MessageSquareText,
  Plus,
  Send,
  Sparkles,
  Wrench,
} from "lucide-react";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";

import { listAgents } from "@/api/agents";
import { getChat, listChats, streamChat } from "@/api/chats";
import { renderToolResult } from "@/components/tool-results";
import { Badge, Button, Card } from "@/components/ui";
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
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const agents = agentsQuery.data ?? [];
  const chats = chatsQuery.data ?? [];

  useEffect(() => {
    if (!selectedAgentId && agents.length > 0) {
      setSelectedAgentId(agents[0].id);
    }
  }, [agents, selectedAgentId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [view?.messages.length, view?.toolEvents.length]);

  // Auto-grow textarea up to ~6 rows
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
  }, [input]);

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
          { role: "user", content, created_at: new Date().toISOString() },
          { role: "assistant", content: "", created_at: new Date().toISOString() },
        ],
        streaming: true,
        toolEvents: prev?.toolEvents ?? [],
      }));

      abortRef.current = streamChat(agentId, content, view?.id ?? null, {
        onTextDelta: (chunk) => {
          setView((prev) => {
            if (!prev) return prev;
            const msgs = [...prev.messages];
            const last = msgs[msgs.length - 1];
            if (last && last.role === "assistant") {
              msgs[msgs.length - 1] = { ...last, content: last.content + chunk };
            }
            return { ...prev, messages: msgs };
          });
        },
        onToolCall: (info) => {
          setView((prev) =>
            prev
              ? {
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
                }
              : prev,
          );
        },
        onToolResult: (info) => {
          setView((prev) =>
            prev
              ? {
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
                }
              : prev,
          );
        },
        onDone: (info) => {
          setView((prev) =>
            prev ? { ...prev, id: info.chat_id, streaming: false } : prev,
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
                  (last.content ? last.content + "\n\n" : "") + `⚠️ ${message}`,
              };
            }
            return { ...prev, messages: msgs, streaming: false };
          });
        },
      });
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

  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
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
          <div className="border-b border-zinc-200/70 bg-white/80 px-6 py-3 backdrop-blur-sm">
            <div className="flex items-center gap-2">
              <div className="inline-flex h-7 w-7 items-center justify-center rounded-lg bg-atea-50 text-atea-600">
                <Bot className="h-4 w-4" />
              </div>
              <h2 className="text-base font-semibold">{selectedAgent.name}</h2>
              <Badge tone="atea">{selectedAgent.model}</Badge>
            </div>
            <p className="mt-1 text-xs text-zinc-500">
              {selectedAgent.description}
            </p>
          </div>
        )}

        <div
          ref={scrollRef}
          className="flex-1 space-y-4 overflow-y-auto px-6 py-6"
        >
          {view?.messages.map((m, i) => {
            const isLast = i === (view?.messages.length ?? 0) - 1;
            return (
              <Message
                key={`m-${i}`}
                message={m}
                streaming={Boolean(view?.streaming) && isLast}
              />
            );
          })}
          {view?.toolEvents.length ? (
            <div className="space-y-2">
              {view.toolEvents.map((ev) => (
                <ToolBlock key={`t-${ev.id}`} event={ev} />
              ))}
            </div>
          ) : null}
          {!view && <EmptyState agent={selectedAgent} />}
        </div>

        <div className="border-t border-zinc-200/70 bg-white/80 p-4 backdrop-blur-sm">
          <div className="mx-auto max-w-4xl">
            <div className="flex items-end gap-2 rounded-2xl border border-zinc-200 bg-white p-2 shadow-soft focus-within:border-atea-400 focus-within:ring-2 focus-within:ring-atea-500/20">
              <textarea
                ref={textareaRef}
                rows={1}
                placeholder={
                  view?.streaming
                    ? "Venter på svar…"
                    : "Skriv en melding…  (Enter sender · Shift+Enter ny linje)"
                }
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={onKey}
                disabled={view?.streaming}
                className="flex-1 resize-none bg-transparent px-2 py-2 text-sm placeholder:text-zinc-400 focus:outline-none disabled:opacity-60"
                style={{ minHeight: "40px", maxHeight: "180px" }}
              />
              <Button
                size="icon"
                onClick={handleSubmit}
                disabled={view?.streaming || !input.trim()}
                aria-label="Send"
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function EmptyState({ agent }: { agent: Agent | null }) {
  const suggestions = [
    "Finn Azure-konsulenter i region Sør",
    "Hvem har Terraform og er mest ledig?",
    "Vis CV-en til Aaron Jimenez",
    "Hvilke skills dekker M365 Sikkerhet?",
  ];
  return (
    <div className="mx-auto mt-20 flex max-w-lg flex-col items-center text-center">
      <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-atea-50 text-atea-600 shadow-soft">
        <Sparkles className="h-6 w-6" />
      </div>
      <h2 className="text-lg font-semibold">
        {agent ? `Chat med ${agent.name}` : "Velg en agent"}
      </h2>
      <p className="mt-1 text-sm text-zinc-500">
        {agent?.description ??
          "Velg en agent i sidemenyen for å komme i gang."}
      </p>
      {agent && (
        <div className="mt-6 flex flex-wrap justify-center gap-2">
          {suggestions.map((s) => (
            <span
              key={s}
              className="rounded-full border border-zinc-200 bg-white px-3 py-1.5 text-xs text-zinc-600"
            >
              {s}
            </span>
          ))}
        </div>
      )}
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
    <aside className="flex w-72 flex-col border-r border-zinc-200/70 bg-white/60 backdrop-blur-sm">
      <div className="border-b border-zinc-200/70 p-3">
        <Button onClick={onNewChat} className="w-full gap-1.5" size="sm">
          <Plus className="h-3.5 w-3.5" />
          Ny samtale
        </Button>
      </div>
      <div className="border-b border-zinc-200/70 p-3">
        <div className="mb-2 px-2 text-[11px] font-medium uppercase tracking-wider text-zinc-500">
          Agenter
        </div>
        <div className="space-y-1">
          {agents.map((a) => {
            const active = selectedAgentId === a.id;
            return (
              <button
                key={a.id}
                onClick={() => onSelectAgent(a.id)}
                className={`group flex w-full items-start gap-2 rounded-lg px-2.5 py-2 text-left text-sm transition-all ${
                  active
                    ? "bg-zinc-900 text-white shadow-soft"
                    : "text-zinc-700 hover:bg-zinc-100"
                }`}
              >
                <Bot
                  className={`mt-0.5 h-4 w-4 shrink-0 ${
                    active ? "text-atea-200" : "text-zinc-400"
                  }`}
                />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-[13px] font-medium">
                    {a.name}
                  </div>
                  <div
                    className={`truncate text-[11px] ${
                      active ? "text-zinc-300" : "text-zinc-500"
                    }`}
                  >
                    {a.description}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-3">
        <div className="mb-2 flex items-center gap-2 px-2 text-[11px] font-medium uppercase tracking-wider text-zinc-500">
          <MessageSquareText className="h-3 w-3" />
          Samtaler
        </div>
        <div className="space-y-0.5">
          {chats.map((c) => (
            <button
              key={c.id}
              onClick={() => onOpenChat(c)}
              className={`w-full truncate rounded-lg px-2.5 py-2 text-left text-sm transition-colors ${
                activeChatId === c.id
                  ? "bg-atea-50 text-atea-900 ring-1 ring-atea-200"
                  : "hover:bg-zinc-100"
              }`}
            >
              <div className="truncate text-[13px] font-medium">{c.title}</div>
              <div className="truncate text-[11px] text-zinc-500">
                {relativeTime(c.updated_at)} · {c.message_count} msg
              </div>
            </button>
          ))}
          {chats.length === 0 && (
            <div className="px-2 text-xs text-zinc-400">
              Ingen samtaler ennå.
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}

function Message({
  message,
  streaming,
}: {
  message: ChatMessage;
  streaming: boolean;
}) {
  if (message.role === "tool" || message.role === "system") return null;
  const isUser = message.role === "user";
  const showCaret = streaming && message.role === "assistant";
  return (
    <div
      className={`flex animate-fade-in ${
        isUser ? "justify-end" : "justify-start"
      }`}
    >
      <div
        className={`max-w-[80%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed shadow-soft ${
          isUser
            ? "rounded-br-md bg-zinc-900 text-white"
            : "rounded-bl-md border border-zinc-200 bg-white text-zinc-900"
        }`}
      >
        {message.content || (isUser ? "" : " ")}
        {showCaret && <span className="caret-blink" />}
      </div>
    </div>
  );
}

function ToolBlock({ event }: { event: ToolEvent }) {
  const done = event.state === "done";
  return (
    <Card className="animate-fade-in border-zinc-200/70 bg-gradient-to-br from-zinc-50 to-white p-3 text-xs">
      <div className="flex items-center gap-2 text-zinc-700">
        <div
          className={`inline-flex h-6 w-6 items-center justify-center rounded-md ${
            done ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"
          }`}
        >
          <Wrench className="h-3.5 w-3.5" />
        </div>
        <span className="font-mono text-[12px] font-semibold text-zinc-800">
          {event.name}
        </span>
        <Badge tone={done ? "green" : "amber"}>
          {done ? "ferdig" : "kjører…"}
        </Badge>
        {event.truncated && <Badge tone="amber">trunkert</Badge>}
      </div>

      {event.content && (
        <div className="mt-3">{renderToolResult(event.name, event.content)}</div>
      )}

      <div className="mt-2 flex gap-3 text-[11px]">
        {event.arguments !== undefined && (
          <details className="text-zinc-500">
            <summary className="cursor-pointer select-none hover:text-zinc-700">
              Argumenter
            </summary>
            <pre className="mt-1 overflow-x-auto rounded-md bg-white p-2 ring-1 ring-zinc-200">
              {JSON.stringify(event.arguments, null, 2)}
            </pre>
          </details>
        )}
        {event.content && (
          <details className="text-zinc-500">
            <summary className="cursor-pointer select-none hover:text-zinc-700">
              Rå JSON
            </summary>
            <pre className="mt-1 max-h-64 overflow-auto rounded-md bg-white p-2 ring-1 ring-zinc-200">
              {event.content}
            </pre>
          </details>
        )}
      </div>
    </Card>
  );
}

function relativeTime(iso: string): string {
  const d = new Date(iso);
  const diffMs = Date.now() - d.getTime();
  const mins = Math.floor(diffMs / 60_000);
  if (mins < 1) return "nå nettopp";
  if (mins < 60) return `${mins} min siden`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}t siden`;
  const days = Math.floor(hrs / 24);
  if (days < 7) return `${days}d siden`;
  return d.toLocaleDateString();
}
