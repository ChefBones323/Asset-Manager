const SOCIAL_BASE = "";

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${SOCIAL_BASE}${url}`, {
    ...init,
    credentials: "include",
  });
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  return res.json();
}

export interface WorkerData {
  workers: Array<{
    worker_id: string;
    status: string;
    jobs_processed: number;
    last_heartbeat?: string;
    last_seen?: string;
  }>;
  active_leases: Array<{
    lease_id: string;
    job_id: string;
    worker_id: string;
    acquired_at: string;
    expires_at: string;
  }>;
  dead_letter_queue: Array<{
    job_id: string;
    retry_count: number;
    reason: string;
    timestamp: string;
  }>;
  retry_counts: Record<string, number>;
  total_leases: number;
}

export interface EventMetrics {
  events_per_second: number;
  events_by_domain: Record<string, number>;
  total_events: number;
  recent_events: number;
  queue_depth: number;
  retry_count: number;
  retry_rate: number;
  dead_letter_count: number;
  dead_letter_rate: number;
}

export interface GovernanceProposal {
  proposal_id: string;
  author_id: string;
  title: string;
  description: string;
  proposal_type: string;
  domain: string;
  status: string;
  payload: Record<string, unknown>;
  quorum: number;
  approval_threshold: number;
  created_at: string;
  votes_for?: number;
  votes_against?: number;
  total_votes?: number;
}

export interface EventRecord {
  event_id: string;
  event_sequence?: number;
  domain: string;
  event_type: string;
  actor_id: string;
  payload: Record<string, unknown>;
  timestamp: string;
}

export interface TrustProfile {
  user_id: string;
  trust_score: number;
  positive_events: number;
  negative_events: number;
  total_events: number;
}

export interface FeedPolicy {
  policy_id: string;
  timestamp_weight: number;
  reaction_weight: number;
  trust_weight: number;
  policy_weight: number;
  status: string;
  version: string;
  approved: boolean;
}

export const socialApi = {
  getWorkers: () => fetchJson<WorkerData>("/admin/workers"),
  getEventMetrics: (window = 60) => fetchJson<EventMetrics>(`/admin/event_metrics?window=${window}`),
  getEvents: (params?: { domain?: string; actor_id?: string; event_type?: string; limit?: number; offset?: number }) => {
    const q = new URLSearchParams();
    if (params?.domain) q.set("domain", params.domain);
    if (params?.actor_id) q.set("actor_id", params.actor_id);
    if (params?.event_type) q.set("event_type", params.event_type);
    if (params?.limit) q.set("limit", String(params.limit));
    if (params?.offset) q.set("offset", String(params.offset));
    return fetchJson<{ events: EventRecord[]; total: number }>(`/admin/events?${q}`);
  },
  getGovernanceProposals: (status?: string) => {
    const q = status ? `?status=${status}` : "";
    return fetchJson<GovernanceProposal[]>(`/api/governance/proposals${q}`);
  },
  getProposal: (id: string) => fetchJson<GovernanceProposal>(`/api/governance/proposal/${id}`),
  getTrustProfile: (userId: string) => fetchJson<TrustProfile>(`/api/trust/profile/${userId}`),
  getFeedPolicies: () => fetchJson<{ policies: FeedPolicy[]; active_count: number; total_count: number }>("/admin/feed_policies"),
  getFeedExplain: (userId: string, contentId: string) =>
    fetchJson<Record<string, unknown>>(`/admin/feed_explain?user_id=${userId}&content_id=${contentId}`),
};
