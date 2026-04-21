import { api } from "@/api/client";
import type { Agent } from "@/types";

export async function listAgents(): Promise<Agent[]> {
  const r = await api.get<Agent[]>("/agents");
  return r.data;
}

export async function getAgent(id: string): Promise<Agent> {
  const r = await api.get<Agent>(`/agents/${id}`);
  return r.data;
}

export async function createAgent(input: Partial<Agent>): Promise<Agent> {
  const r = await api.post<Agent>("/agents", input);
  return r.data;
}

export async function updateAgent(id: string, patch: Partial<Agent>): Promise<Agent> {
  const r = await api.patch<Agent>(`/agents/${id}`, patch);
  return r.data;
}

export async function deleteAgent(id: string): Promise<void> {
  await api.delete(`/agents/${id}`);
}
