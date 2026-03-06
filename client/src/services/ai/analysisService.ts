import { useEventStore, type PlatformEvent } from "@/store/eventStore";
import { reconstructState } from "@/services/replay/replayService";

export interface AnalysisResult {
  type: "ranking" | "trust" | "policy" | "influence" | "event_chain";
  title: string;
  summary: string;
  details: string[];
  referencedEvents: string[];
  confidence: number;
}

export interface SuggestedQuery {
  id: string;
  label: string;
  description: string;
  action: string;
}

export const SUGGESTED_QUERIES: SuggestedQuery[] = [
  { id: "feed_analysis", label: "Analyze Feed Rankings", description: "Explain current feed ranking factors and weights", action: "analyzeFeedRanking" },
  { id: "trust_overview", label: "Trust Network Overview", description: "Identify top trusted actors and network patterns", action: "findInfluentialNodes" },
  { id: "policy_impact", label: "Policy Impact Analysis", description: "Trace how policy changes affected content ranking", action: "tracePolicyImpact" },
  { id: "event_summary", label: "Event Stream Summary", description: "Summarize recent system activity by domain", action: "summarizeEvents" },
  { id: "anomaly_check", label: "Anomaly Detection", description: "Identify unusual patterns in event flow", action: "detectAnomalies" },
];

function getEvents(): PlatformEvent[] {
  return useEventStore.getState().events;
}

export function analyzeFeedRanking(postId?: string): AnalysisResult {
  const events = getEvents();
  const contentEvents = events.filter((e) => e.domain === "content");
  const policyEvents = events.filter((e) => e.domain === "feed_policy" || e.event_type === "policy_activated");
  const referencedEvents: string[] = [];

  const details: string[] = [];

  if (contentEvents.length === 0) {
    details.push("No content events found in the current event buffer.");
    details.push("Feed ranking analysis requires content_created events with ranking metadata.");
  } else {
    details.push(`${contentEvents.length} content events found in buffer.`);

    const postEvents = contentEvents.filter((e) => e.event_type === "content_created");
    details.push(`${postEvents.length} posts created in current window.`);

    if (postId) {
      const target = contentEvents.find((e) => e.event_id === postId || e.payload.content_id === postId);
      if (target) {
        referencedEvents.push(target.event_id);
        details.push(`Post ${postId} created by ${target.actor_id} at ${target.timestamp}.`);
        if (target.payload.platforms) {
          details.push(`Published to platforms: ${(target.payload.platforms as string[]).join(", ")}.`);
        }
      } else {
        details.push(`Post ${postId} not found in current event buffer.`);
      }
    }
  }

  if (policyEvents.length > 0) {
    const latest = policyEvents[policyEvents.length - 1];
    referencedEvents.push(latest.event_id);
    details.push(`Active policy: ${latest.payload.policy_id || "unknown"} (applied at ${latest.timestamp}).`);
    details.push("Feed ranking uses weights: timestamp (recency), reaction count, trust score, and policy modifier.");
  }

  return {
    type: "ranking",
    title: "Feed Ranking Analysis",
    summary: `Analyzed ${contentEvents.length} content events with ${policyEvents.length} policy configurations.`,
    details,
    referencedEvents,
    confidence: contentEvents.length > 0 ? 0.85 : 0.3,
  };
}

export function explainTrustScore(userId?: string): AnalysisResult {
  const events = getEvents();
  const trustEvents = events.filter((e) => e.domain === "trust");
  const referencedEvents: string[] = [];
  const details: string[] = [];

  if (trustEvents.length === 0) {
    details.push("No trust events found in current buffer.");
    details.push("Trust scores derive exclusively from trust_events domain.");
  } else {
    details.push(`${trustEvents.length} trust events in buffer.`);

    if (userId) {
      const userEvents = trustEvents.filter((e) => e.actor_id === userId);
      if (userEvents.length > 0) {
        for (const e of userEvents.slice(-3)) referencedEvents.push(e.event_id);
        const latest = userEvents[userEvents.length - 1];
        details.push(`User ${userId} has ${userEvents.length} trust events.`);
        if (latest.payload.trust_score !== undefined) {
          details.push(`Current trust score: ${latest.payload.trust_score}.`);
        }
        details.push(`Most recent trust event: ${latest.event_type} at ${latest.timestamp}.`);
      } else {
        details.push(`No trust events found for user ${userId}.`);
      }
    }

    const actors = new Set(trustEvents.map((e) => e.actor_id));
    details.push(`${actors.size} unique actors with trust activity.`);
  }

  return {
    type: "trust",
    title: "Trust Score Explanation",
    summary: `${trustEvents.length} trust events analyzed${userId ? ` for user ${userId.slice(0, 12)}` : ""}.`,
    details,
    referencedEvents,
    confidence: trustEvents.length > 0 ? 0.8 : 0.2,
  };
}

export function tracePolicyImpact(policyVersion?: string): AnalysisResult {
  const events = getEvents();
  const policyEvents = events.filter((e) => e.domain === "feed_policy" || e.event_type === "policy_activated" || e.event_type === "config_changed");
  const contentAfterPolicy: PlatformEvent[] = [];
  const referencedEvents: string[] = [];
  const details: string[] = [];

  if (policyEvents.length === 0) {
    details.push("No policy events found in current buffer.");
  } else {
    details.push(`${policyEvents.length} policy/config events found.`);

    let targetPolicy = policyEvents[policyEvents.length - 1];
    if (policyVersion) {
      const match = policyEvents.find((e) => e.payload.policy_version === policyVersion || e.payload.policy_id === policyVersion);
      if (match) targetPolicy = match;
    }

    referencedEvents.push(targetPolicy.event_id);
    details.push(`Policy event: ${targetPolicy.event_type} at ${targetPolicy.timestamp}.`);

    if (targetPolicy.payload.timestamp_weight !== undefined) {
      details.push(`Weights — Recency: ${targetPolicy.payload.timestamp_weight}, Reactions: ${targetPolicy.payload.reaction_weight}, Trust: ${targetPolicy.payload.trust_weight}, Policy: ${targetPolicy.payload.policy_weight}.`);
    }

    const policyTime = new Date(targetPolicy.timestamp).getTime();
    const after = events.filter((e) => e.domain === "content" && new Date(e.timestamp).getTime() > policyTime);
    details.push(`${after.length} content events occurred after this policy change.`);
  }

  return {
    type: "policy",
    title: "Policy Impact Trace",
    summary: `Traced impact of ${policyEvents.length} policy changes on content events.`,
    details,
    referencedEvents,
    confidence: policyEvents.length > 0 ? 0.75 : 0.2,
  };
}

export function findInfluentialNodes(): AnalysisResult {
  const events = getEvents();
  const actorActivity = new Map<string, { events: number; domains: Set<string>; lastSeen: string }>();
  const referencedEvents: string[] = [];
  const details: string[] = [];

  for (const e of events) {
    if (!e.actor_id || e.actor_id === "social-publisher-worker") continue;
    const entry = actorActivity.get(e.actor_id) || { events: 0, domains: new Set(), lastSeen: "" };
    entry.events++;
    entry.domains.add(e.domain);
    entry.lastSeen = e.timestamp;
    actorActivity.set(e.actor_id, entry);
  }

  const sorted = Array.from(actorActivity.entries()).sort((a, b) => b[1].events - a[1].events);

  details.push(`${actorActivity.size} unique actors identified.`);

  for (const [actor, data] of sorted.slice(0, 5)) {
    details.push(`${actor.slice(0, 16)}: ${data.events} events across [${Array.from(data.domains).join(", ")}], last active ${data.lastSeen}.`);
  }

  if (sorted.length > 0) {
    const topEvents = events.filter((e) => e.actor_id === sorted[0][0]).slice(-2);
    for (const e of topEvents) referencedEvents.push(e.event_id);
  }

  return {
    type: "influence",
    title: "Influential Node Analysis",
    summary: `${actorActivity.size} actors analyzed. Top actor has ${sorted[0]?.[1]?.events ?? 0} events.`,
    details,
    referencedEvents,
    confidence: actorActivity.size > 2 ? 0.8 : 0.4,
  };
}

export function explainEventChain(eventId: string): AnalysisResult {
  const events = getEvents();
  const target = events.find((e) => e.event_id === eventId);
  const referencedEvents: string[] = [];
  const details: string[] = [];

  if (!target) {
    return {
      type: "event_chain",
      title: "Event Chain Analysis",
      summary: `Event ${eventId} not found in buffer.`,
      details: [`Event ${eventId} is not in the current 200-event buffer. Try fetching from the Event Explorer.`],
      referencedEvents: [],
      confidence: 0,
    };
  }

  referencedEvents.push(target.event_id);
  details.push(`Event: ${target.event_type} in domain ${target.domain}.`);
  details.push(`Actor: ${target.actor_id} at ${target.timestamp}.`);
  details.push(`Payload keys: ${Object.keys(target.payload).join(", ") || "empty"}.`);

  const sameActor = events.filter((e) => e.actor_id === target.actor_id && e.event_id !== target.event_id);
  if (sameActor.length > 0) {
    details.push(`Actor ${target.actor_id.slice(0, 12)} has ${sameActor.length} other events in buffer.`);
    const before = sameActor.filter((e) => new Date(e.timestamp) < new Date(target.timestamp));
    const after = sameActor.filter((e) => new Date(e.timestamp) > new Date(target.timestamp));
    if (before.length > 0) {
      const prev = before[before.length - 1];
      referencedEvents.push(prev.event_id);
      details.push(`Previous: ${prev.event_type} at ${prev.timestamp}.`);
    }
    if (after.length > 0) {
      const next = after[0];
      referencedEvents.push(next.event_id);
      details.push(`Next: ${next.event_type} at ${next.timestamp}.`);
    }
  }

  if (target.payload.source_event_id) {
    const source = events.find((e) => e.event_id === target.payload.source_event_id);
    if (source) {
      referencedEvents.push(source.event_id);
      details.push(`Triggered by source event: ${source.event_type} (${source.event_id.slice(0, 16)}).`);
    }
  }

  return {
    type: "event_chain",
    title: "Event Chain Analysis",
    summary: `Traced event ${eventId.slice(0, 16)} with ${referencedEvents.length} related events.`,
    details,
    referencedEvents,
    confidence: 0.9,
  };
}

export function summarizeEvents(): AnalysisResult {
  const events = getEvents();
  const state = reconstructState(events);
  const domainCounts = new Map<string, number>();
  const typeCounts = new Map<string, number>();

  for (const e of events) {
    domainCounts.set(e.domain, (domainCounts.get(e.domain) ?? 0) + 1);
    typeCounts.set(e.event_type, (typeCounts.get(e.event_type) ?? 0) + 1);
  }

  const details: string[] = [
    `Total events in buffer: ${events.length}.`,
    `Domains: ${Array.from(domainCounts.entries()).map(([d, c]) => `${d}(${c})`).join(", ")}.`,
    `Top event types: ${Array.from(typeCounts.entries()).sort((a, b) => b[1] - a[1]).slice(0, 5).map(([t, c]) => `${t}(${c})`).join(", ")}.`,
    `Feed: ${state.feed.totalPosts} posts, policy: ${state.feed.lastPolicyVersion || "default"}.`,
    `Trust: ${state.trust.trustUpdates} updates, avg score: ${state.trust.averageTrust.toFixed(1)}.`,
    `Governance: ${state.governance.totalProposals} proposals, ${state.governance.approvedProposals} approved.`,
    `Workers: ${state.workers.heartbeatCount} heartbeats, ${state.workers.publishEvents} publishes.`,
  ];

  return {
    type: "influence",
    title: "System Event Summary",
    summary: `${events.length} events across ${domainCounts.size} domains.`,
    details,
    referencedEvents: [],
    confidence: events.length > 0 ? 0.9 : 0.1,
  };
}

export function detectAnomalies(): AnalysisResult {
  const events = getEvents();
  const details: string[] = [];
  const referencedEvents: string[] = [];

  const failures = events.filter((e) => e.event_type === "platform_publish_failed");
  if (failures.length > 0) {
    details.push(`${failures.length} platform publish failures detected.`);
    for (const f of failures.slice(-3)) {
      referencedEvents.push(f.event_id);
      details.push(`  Failed: ${f.payload.platform} at ${f.timestamp} — ${f.payload.error || "unknown error"}.`);
    }
  }

  const actorCounts = new Map<string, number>();
  for (const e of events) {
    actorCounts.set(e.actor_id, (actorCounts.get(e.actor_id) ?? 0) + 1);
  }
  const avgActivity = events.length / Math.max(actorCounts.size, 1);
  for (const [actor, count] of actorCounts) {
    if (count > avgActivity * 3 && count > 5) {
      details.push(`High activity actor: ${actor.slice(0, 16)} with ${count} events (avg: ${avgActivity.toFixed(1)}).`);
    }
  }

  if (details.length === 0) {
    details.push("No anomalies detected in current event buffer.");
  }

  return {
    type: "event_chain",
    title: "Anomaly Detection",
    summary: `Scanned ${events.length} events. ${failures.length} failures detected.`,
    details,
    referencedEvents,
    confidence: events.length > 10 ? 0.7 : 0.3,
  };
}

export function processQuery(query: string): AnalysisResult {
  const lower = query.toLowerCase();

  if (lower.includes("rank") || lower.includes("feed") || lower.includes("post")) {
    return analyzeFeedRanking();
  }
  if (lower.includes("trust") || lower.includes("score") || lower.includes("reputation")) {
    return explainTrustScore();
  }
  if (lower.includes("policy") || lower.includes("weight") || lower.includes("config")) {
    return tracePolicyImpact();
  }
  if (lower.includes("influence") || lower.includes("actor") || lower.includes("node") || lower.includes("network")) {
    return findInfluentialNodes();
  }
  if (lower.includes("anomal") || lower.includes("error") || lower.includes("fail")) {
    return detectAnomalies();
  }
  if (lower.includes("summary") || lower.includes("overview") || lower.includes("status")) {
    return summarizeEvents();
  }
  if (lower.includes("event") && (lower.includes("chain") || lower.includes("trace"))) {
    return explainEventChain(lower.replace(/.*event\s+/, "").trim());
  }

  return summarizeEvents();
}
