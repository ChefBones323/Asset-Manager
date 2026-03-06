import { useEventStore, type PlatformEvent } from "@/store/eventStore";
import { socialApi } from "@/services/api";

export interface ReplayState {
  feed: ReplayFeedState;
  trust: ReplayTrustState;
  governance: ReplayGovernanceState;
  workers: ReplayWorkerState;
}

export interface ReplayFeedState {
  totalPosts: number;
  activePolicies: string[];
  lastPolicyVersion: string;
  recentPosts: Array<{ content_id: string; author_id: string; timestamp: string }>;
}

export interface ReplayTrustState {
  totalUsers: number;
  trustUpdates: number;
  averageTrust: number;
  topActors: Array<{ actor_id: string; score: number }>;
}

export interface ReplayGovernanceState {
  totalProposals: number;
  approvedProposals: number;
  rejectedProposals: number;
  activeProposals: number;
  policyChanges: number;
}

export interface ReplayWorkerState {
  heartbeatCount: number;
  activeWorkers: Set<string>;
  lastHeartbeat: string | null;
  publishEvents: number;
  failedPublishes: number;
}

export function reconstructState(events: PlatformEvent[], upToEventId?: string): ReplayState {
  const state: ReplayState = {
    feed: { totalPosts: 0, activePolicies: [], lastPolicyVersion: "", recentPosts: [] },
    trust: { totalUsers: 0, trustUpdates: 0, averageTrust: 0, topActors: [] },
    governance: { totalProposals: 0, approvedProposals: 0, rejectedProposals: 0, activeProposals: 0, policyChanges: 0 },
    workers: { heartbeatCount: 0, activeWorkers: new Set(), lastHeartbeat: null, publishEvents: 0, failedPublishes: 0 },
  };

  const trustScores = new Map<string, number>();
  const seenUsers = new Set<string>();

  for (const event of events) {
    applyEvent(state, event, trustScores, seenUsers);
    if (upToEventId && event.event_id === upToEventId) break;
  }

  state.trust.totalUsers = seenUsers.size;
  if (trustScores.size > 0) {
    const scores = Array.from(trustScores.values());
    state.trust.averageTrust = scores.reduce((a, b) => a + b, 0) / scores.length;
    state.trust.topActors = Array.from(trustScores.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(([actor_id, score]) => ({ actor_id, score }));
  }

  return state;
}

function applyEvent(
  state: ReplayState,
  event: PlatformEvent,
  trustScores: Map<string, number>,
  seenUsers: Set<string>
): void {
  if (event.actor_id) seenUsers.add(event.actor_id);

  switch (event.domain) {
    case "content":
      if (event.event_type === "content_created") {
        state.feed.totalPosts++;
        state.feed.recentPosts.push({
          content_id: (event.payload.content_id as string) || event.event_id,
          author_id: event.actor_id,
          timestamp: event.timestamp,
        });
        if (state.feed.recentPosts.length > 10) state.feed.recentPosts.shift();
      }
      if (event.event_type.includes("_post_sent")) {
        state.workers.publishEvents++;
      }
      if (event.event_type === "platform_publish_failed") {
        state.workers.failedPublishes++;
      }
      break;

    case "trust":
      state.trust.trustUpdates++;
      if (event.payload.trust_score !== undefined) {
        trustScores.set(event.actor_id, event.payload.trust_score as number);
      }
      break;

    case "governance":
      if (event.event_type === "proposal_created" || event.event_type === "proposal_submitted") {
        state.governance.totalProposals++;
        state.governance.activeProposals++;
      }
      if (event.event_type === "proposal_approved") {
        state.governance.approvedProposals++;
        state.governance.activeProposals = Math.max(0, state.governance.activeProposals - 1);
      }
      if (event.event_type === "proposal_rejected") {
        state.governance.rejectedProposals++;
        state.governance.activeProposals = Math.max(0, state.governance.activeProposals - 1);
      }
      if (event.event_type === "policy_activated" || event.event_type === "config_changed") {
        state.governance.policyChanges++;
        if (event.payload.policy_version) {
          state.feed.lastPolicyVersion = event.payload.policy_version as string;
        }
      }
      break;

    case "workers":
    case "platform":
      if (event.event_type === "worker_heartbeat") {
        state.workers.heartbeatCount++;
        state.workers.activeWorkers.add(event.actor_id);
        state.workers.lastHeartbeat = event.timestamp;
      }
      break;

    case "feed_policy":
      state.governance.policyChanges++;
      if (event.payload.policy_id) {
        state.feed.activePolicies = [...new Set([...state.feed.activePolicies, event.payload.policy_id as string])];
      }
      break;
  }
}

export function getEventsFromStore(): PlatformEvent[] {
  return useEventStore.getState().events;
}

export async function fetchHistoricalEvents(params?: {
  domain?: string;
  event_type?: string;
  actor_id?: string;
  limit?: number;
  offset?: number;
}): Promise<{ events: PlatformEvent[]; total: number }> {
  try {
    const result = await socialApi.getEvents({
      ...params,
      limit: params?.limit ?? 100,
      offset: params?.offset ?? 0,
    });
    return { events: result.events as PlatformEvent[], total: result.total };
  } catch {
    return { events: getEventsFromStore(), total: getEventsFromStore().length };
  }
}
