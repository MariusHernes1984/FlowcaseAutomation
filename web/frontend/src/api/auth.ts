import { api, setAccessToken } from "@/api/client";
import type { LoginResponse, User } from "@/types";

export async function login(email: string, password: string): Promise<LoginResponse> {
  const r = await api.post<LoginResponse>("/auth/login", { email, password });
  setAccessToken(r.data.access_token);
  return r.data;
}

export async function logout(): Promise<void> {
  try {
    await api.post("/auth/logout");
  } finally {
    setAccessToken(null);
  }
}

export async function refresh(): Promise<LoginResponse> {
  const r = await api.post<LoginResponse>("/auth/refresh");
  setAccessToken(r.data.access_token);
  return r.data;
}

export async function me(): Promise<User> {
  const r = await api.get<User>("/auth/me");
  return r.data;
}

/** Admin-only endpoints — callers must be role=admin. */
export async function listUsers(): Promise<User[]> {
  const r = await api.get<User[]>("/auth/users");
  return r.data;
}

export async function createUser(input: {
  email: string;
  name: string;
  password: string;
  role?: "admin" | "user";
}): Promise<User> {
  const r = await api.post<User>("/auth/users", input);
  return r.data;
}

export async function updateUser(
  id: string,
  patch: Partial<{ name: string; password: string; role: "admin" | "user"; is_active: boolean }>,
): Promise<User> {
  const r = await api.patch<User>(`/auth/users/${id}`, patch);
  return r.data;
}
