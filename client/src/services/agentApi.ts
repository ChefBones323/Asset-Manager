const PYTHON_API = "http://localhost:8000";

export interface AgentToolCall {
  step: number;
  tool: string;
  args: Record<string, unknown>;
  description: string;
}

export interface AgentToolResult {
  status: string;
  tool?: string;
  result?: Record<string, unknown>;
  error?: string;
  approval?: string;
  proposal_id?: string;
  approval_level?: string;
  requires_human_approval?: boolean;
  message?: string;
}

export interface AgentRunResult {
  status: string;
  user_input: string;
  plan: string[];
  tool_calls: AgentToolCall[];
  results: AgentToolResult[];
  steps_executed: number;
  confidence: number;
  error: string | null;
  system_prompt?: string;
}

export interface AgentMemoryEntry {
  id: string;
  category: string;
  key: string;
  value: string;
  created_at: string;
  updated_at: string;
}

export interface AgentToolSpec {
  name: string;
  description: string;
  input_schema: Record<string, unknown>;
}

export interface AgentPolicies {
  [tool: string]: string;
}

export interface ScheduledTask {
  task_id: string;
  name: string;
  description: string;
  interval_seconds: number;
  last_run: string | null;
  run_count: number;
  enabled: boolean;
}

async function agentFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${PYTHON_API}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `Agent API error: ${res.status}`);
  }
  return res.json();
}

export async function runAgentTask(task: string): Promise<AgentRunResult> {
  return agentFetch<AgentRunResult>("/admin/agent/run", {
    method: "POST",
    body: JSON.stringify({ task }),
  });
}

export async function getAgentMemory(
  category?: string,
  limit = 50
): Promise<{ memories: AgentMemoryEntry[]; total: number }> {
  const params = new URLSearchParams();
  if (category) params.set("category", category);
  params.set("limit", String(limit));
  return agentFetch(`/admin/agent/memory?${params}`);
}

export interface GovernedActionResponse {
  status: string;
  proposal_id: string;
  execution_id?: string;
  message: string;
  id?: string;
}

export async function storeAgentMemory(
  category: string,
  key: string,
  value: string
): Promise<GovernedActionResponse> {
  return agentFetch<GovernedActionResponse>("/admin/agent/memory", {
    method: "POST",
    body: JSON.stringify({ category, key, value }),
  });
}

export async function deleteAgentMemory(id: string): Promise<GovernedActionResponse> {
  return agentFetch(`/admin/agent/memory/${id}`, { method: "DELETE" });
}

export async function getAgentTools(): Promise<{
  tools: AgentToolSpec[];
  policies: AgentPolicies;
}> {
  return agentFetch("/admin/agent/tools");
}

export async function getSchedulerStatus(): Promise<{
  running: boolean;
  tasks: ScheduledTask[];
}> {
  return agentFetch("/admin/agent/scheduler");
}

export async function runScheduledTask(
  taskId: string
): Promise<{ status: string; task: string; result: Record<string, unknown> }> {
  return agentFetch(`/admin/agent/scheduler/${taskId}/run`, { method: "POST" });
}
