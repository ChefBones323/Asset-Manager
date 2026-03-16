const PYTHON_API = "http://localhost:8000";

export interface WorkerNodeData {
  id: string;
  hostname: string;
  status: "idle" | "busy" | "unhealthy";
  capabilities: string[];
  last_heartbeat: string | null;
  heartbeat_age_seconds: number | null;
  current_job_id: string | null;
  created_at: string;
}

export interface QueueDepthData {
  queued: number;
  claimed: number;
  running: number;
  completed: number;
  failed: number;
  dlq: number;
  total: number;
}

export interface DLQEntry {
  id: string;
  job_id: string;
  error_message: string;
  failed_at: string;
}

export interface JobEntry {
  id: string;
  proposal_id: string;
  tool_name: string;
  payload: Record<string, unknown>;
  status: string;
  retry_count: number;
  max_retries: number;
  claimed_by_worker: string | null;
  created_at: string;
  updated_at: string;
}

export interface WorkersResponse {
  workers: WorkerNodeData[];
  queue_depth: QueueDepthData;
  dead_letter_queue: DLQEntry[];
  total_workers: number;
}

export interface MetricsData {
  active_workers: number;
  busy_workers: number;
  unhealthy_workers: number;
  total_workers: number;
  queue_depth: number;
  queue_running: number;
  jobs_processed_total: number;
  jobs_failed_total: number;
  dlq_count: number;
  retry_rate: number;
}

async function workerFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${PYTHON_API}${path}`, {
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `Worker API error: ${res.status}`);
  }
  return res.json();
}

export async function fetchWorkers(): Promise<WorkersResponse> {
  return workerFetch<WorkersResponse>("/admin/workers");
}

export async function fetchQueueDepth(): Promise<QueueDepthData> {
  return workerFetch<QueueDepthData>("/admin/queue/depth");
}

export async function fetchQueueJobs(status?: string, limit = 50): Promise<{ jobs: JobEntry[] }> {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  params.set("limit", String(limit));
  return workerFetch(`/admin/queue/jobs?${params}`);
}

export async function fetchMetrics(): Promise<MetricsData> {
  return workerFetch<MetricsData>("/metrics");
}
