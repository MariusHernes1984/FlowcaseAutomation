import { useEffect, useState } from "react";

import { Button, Card, Input, Label, Textarea } from "@/components/ui";
import type { Agent } from "@/types";

const AVAILABLE_TOOLS: { id: string; label: string }[] = [
  { id: "*", label: "Alle tools (wildcard)" },
  { id: "flowcase_list_offices", label: "flowcase_list_offices" },
  { id: "flowcase_list_regions", label: "flowcase_list_regions" },
  { id: "flowcase_search_users", label: "flowcase_search_users" },
  { id: "flowcase_find_user", label: "flowcase_find_user" },
  { id: "flowcase_get_cv", label: "flowcase_get_cv" },
  { id: "flowcase_list_skills", label: "flowcase_list_skills" },
  { id: "flowcase_find_users_by_skill", label: "flowcase_find_users_by_skill" },
  { id: "flowcase_get_availability", label: "flowcase_get_availability" },
  { id: "flowcase_list_customers", label: "flowcase_list_customers" },
  { id: "flowcase_list_industries", label: "flowcase_list_industries" },
  { id: "flowcase_find_projects", label: "flowcase_find_projects" },
];

export default function AgentEditor({
  agent,
  isCreating,
  saving,
  onSave,
  onCancel,
  error,
}: {
  agent: Agent;
  isCreating: boolean;
  saving: boolean;
  onSave: (a: Agent) => void;
  onCancel: () => void;
  error: Error | null;
}) {
  const [draft, setDraft] = useState<Agent>(agent);
  useEffect(() => setDraft(agent), [agent]);

  function toggleTool(id: string) {
    setDraft((d) => {
      const set = new Set(d.allowed_tools);
      if (set.has(id)) set.delete(id);
      else set.add(id);
      return { ...d, allowed_tools: Array.from(set) };
    });
  }

  return (
    <Card className="p-5">
      <div className="mb-4">
        <h2 className="text-lg font-semibold">
          {isCreating ? "Ny agent" : `Redigerer: ${agent.name}`}
        </h2>
      </div>
      <div className="space-y-4">
        {isCreating && (
          <div>
            <Label htmlFor="agent-id">ID (slug)</Label>
            <Input
              id="agent-id"
              value={draft.id}
              onChange={(e) => setDraft({ ...draft, id: e.target.value })}
              placeholder="f.eks. skills-oversetter"
              className="mt-1"
            />
          </div>
        )}
        <div>
          <Label htmlFor="agent-name">Navn</Label>
          <Input
            id="agent-name"
            value={draft.name}
            onChange={(e) => setDraft({ ...draft, name: e.target.value })}
            className="mt-1"
          />
        </div>
        <div>
          <Label htmlFor="agent-desc">Beskrivelse</Label>
          <Input
            id="agent-desc"
            value={draft.description}
            onChange={(e) =>
              setDraft({ ...draft, description: e.target.value })
            }
            className="mt-1"
          />
        </div>
        <div>
          <Label htmlFor="agent-prompt">System prompt</Label>
          <Textarea
            id="agent-prompt"
            rows={14}
            value={draft.system_prompt}
            onChange={(e) =>
              setDraft({ ...draft, system_prompt: e.target.value })
            }
            className="mt-1 font-mono text-xs"
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="agent-model">Modell</Label>
            <Input
              id="agent-model"
              value={draft.model}
              onChange={(e) => setDraft({ ...draft, model: e.target.value })}
              placeholder="gpt-5.4-mini"
              className="mt-1"
            />
          </div>
          <div>
            <Label htmlFor="agent-temp">Temperature</Label>
            <Input
              id="agent-temp"
              type="number"
              step="0.1"
              min="0"
              max="2"
              value={draft.temperature}
              onChange={(e) =>
                setDraft({ ...draft, temperature: parseFloat(e.target.value) })
              }
              className="mt-1"
            />
          </div>
        </div>
        <div>
          <Label>Tillatte tools</Label>
          <div className="mt-2 grid grid-cols-2 gap-1">
            {AVAILABLE_TOOLS.map((t) => (
              <label
                key={t.id}
                className="flex items-center gap-2 rounded px-2 py-1 text-sm hover:bg-slate-50"
              >
                <input
                  type="checkbox"
                  checked={draft.allowed_tools.includes(t.id)}
                  onChange={() => toggleTool(t.id)}
                />
                <span className="font-mono text-xs">{t.id}</span>
              </label>
            ))}
          </div>
        </div>
        {error && (
          <div className="rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {(error as { response?: { data?: { detail?: string } } }).response
              ?.data?.detail ?? error.message}
          </div>
        )}
        <div className="flex gap-2 pt-2">
          <Button onClick={() => onSave(draft)} disabled={saving}>
            {saving ? "Lagrer…" : "Lagre"}
          </Button>
          <Button variant="secondary" onClick={onCancel}>
            Avbryt
          </Button>
        </div>
      </div>
    </Card>
  );
}
