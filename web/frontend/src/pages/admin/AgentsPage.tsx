import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { createAgent, deleteAgent, listAgents, updateAgent } from "@/api/agents";
import { Badge, Button, Card } from "@/components/ui";
import type { Agent } from "@/types";

import AgentEditor from "./AgentEditor";

export default function AgentsPage() {
  const qc = useQueryClient();
  const { data: agents = [] } = useQuery({
    queryKey: ["agents"],
    queryFn: listAgents,
  });
  const [editing, setEditing] = useState<Agent | null>(null);
  const [creating, setCreating] = useState(false);

  const saveMutation = useMutation({
    mutationFn: async (a: Agent) => {
      if (creating) {
        return createAgent(a);
      }
      return updateAgent(a.id, a);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["agents"] });
      setEditing(null);
      setCreating(false);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteAgent(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["agents"] }),
  });

  return (
    <div className="mx-auto max-w-5xl p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Agenter</h1>
          <p className="text-sm text-slate-500">
            Rediger system-prompt, modell og tool-tilgang per agent.
          </p>
        </div>
        <Button
          onClick={() => {
            setCreating(true);
            setEditing({
              id: "",
              name: "",
              description: "",
              system_prompt: "",
              model: "gpt-4.1",
              allowed_tools: ["*"],
              temperature: 0.7,
              max_tokens: null,
              is_active: true,
              created_at: "",
              updated_at: "",
            } as Agent);
          }}
        >
          + Ny agent
        </Button>
      </div>

      {editing ? (
        <AgentEditor
          agent={editing}
          isCreating={creating}
          saving={saveMutation.isPending}
          onCancel={() => {
            setEditing(null);
            setCreating(false);
          }}
          onSave={(updated) => saveMutation.mutate(updated)}
          error={saveMutation.error as Error | null}
        />
      ) : (
        <div className="space-y-3">
          {agents.map((a) => (
            <Card key={a.id} className="p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold">{a.name}</h3>
                    <Badge>{a.model}</Badge>
                    {!a.is_active && <Badge tone="red">deaktivert</Badge>}
                  </div>
                  <p className="mt-1 text-sm text-slate-500">{a.description}</p>
                  <div className="mt-2 flex flex-wrap gap-1 text-[11px]">
                    {(a.allowed_tools.length === 0
                      ? ["(ingen)"]
                      : a.allowed_tools
                    ).map((t) => (
                      <Badge key={t} tone="blue">
                        {t}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => {
                      setCreating(false);
                      setEditing(a);
                    }}
                  >
                    Rediger
                  </Button>
                  <Button
                    size="sm"
                    variant="danger"
                    onClick={() => {
                      if (
                        confirm(
                          `Slette agent "${a.name}"? Eksisterende samtaler beholdes.`,
                        )
                      ) {
                        deleteMutation.mutate(a.id);
                      }
                    }}
                  >
                    Slett
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
