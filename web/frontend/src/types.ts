export type Role = "admin" | "user";

export interface User {
  id: string;
  email: string;
  name: string;
  role: Role;
  is_active: boolean;
  created_at: string;
}

export interface Agent {
  id: string;
  name: string;
  description: string;
  system_prompt: string;
  model: string;
  allowed_tools: string[];
  temperature: number;
  max_tokens: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  role: "user" | "assistant" | "tool" | "system";
  content: string;
  tool_calls?: Array<{
    id: string;
    type: string;
    function: { name: string; arguments: string };
  }> | null;
  tool_call_id?: string | null;
  name?: string | null;
  created_at: string;
}

export interface ChatSession {
  id: string;
  userId: string;
  agent_id: string;
  title: string;
  messages: ChatMessage[];
  created_at: string;
  updated_at: string;
}

export interface ChatSessionSummary {
  id: string;
  agent_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}
