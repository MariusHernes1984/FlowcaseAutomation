import { api } from "@/api/client";
import type {
  CustomerItem,
  IndustryItem,
  ListRegionsData,
  SkillItem,
} from "@/components/tool-results/types";

export async function fetchIndustries(query?: string): Promise<IndustryItem[]> {
  const r = await api.get<{ industries: IndustryItem[] }>(
    "/reference/industries",
    { params: { q: query, limit: 100 } },
  );
  return r.data.industries ?? [];
}

export async function fetchCustomers(query?: string): Promise<CustomerItem[]> {
  const r = await api.get<{ customers: CustomerItem[] }>(
    "/reference/customers",
    { params: { q: query, limit: 100 } },
  );
  return r.data.customers ?? [];
}

export async function fetchSkills(query?: string): Promise<SkillItem[]> {
  const r = await api.get<{ skills: SkillItem[] }>("/reference/skills", {
    params: { q: query, limit: 100 },
  });
  return r.data.skills ?? [];
}

export async function fetchRegions(): Promise<ListRegionsData> {
  const r = await api.get<ListRegionsData>("/reference/regions");
  return r.data;
}
