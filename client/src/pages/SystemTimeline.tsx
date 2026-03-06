import { useState, useMemo, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { socialApi, type EventRecord } from "@/services/api";
import { useEventStore, type PlatformEvent } from "@/store/eventStore";
import { reconstructState, type ReplayState } from "@/services/replay/replayService";
import { GlassCard, GlassCardHeader, GlassCardTitle, GlassCardBody } from "@/components/common/Card";
import { GlassModal } from "@/components/common/Modal";
import { Metric, MetricRow } from "@/components/common/Metric";
import { cn } from "@/lib/utils";
import {
  Clock, Rewind, FastForward, Search, Filter,
  Rss, Users, Shield, Server, AlertTriangle,
} from "lucide-react";

const DOMAIN_COLORS: Record<string, string> = {
  content: "bg-signal-blue",
  trust: "bg-signal-green",
  governance: "bg-signal-purple",
  workers: "bg-signal-amber",
  platform: "bg-signal-amber",
  feed_policy: "bg-signal-purple",
};

const DOMAIN_DOT_COLORS: Record<string, string> = {
  content: "text-signal-blue",
  trust: "text-signal-green",
  governance: "text-signal-purple",
  workers: "text-signal-amber",
  platform: "text-signal-amber",
  feed_policy: "text-signal-purple",
};

const ERROR_TYPES = new Set(["platform_publish_failed"]);

function isErrorEvent(event: PlatformEvent): boolean {
  return ERROR_TYPES.has(event.event_type) || event.event_type.includes("failed");
}

export default function SystemTimeline() {
  const storeEvents = useEventStore((s) => s.events);
  const [sliderPos, setSliderPos] = useState(100);
  const [filterDomain, setFilterDomain] = useState("");
  const [filterType, setFilterType] = useState("");
  const [filterActor, setFilterActor] = useState("");
  const [jumpEventId, setJumpEventId] = useState("");
  const [jumpTimestamp, setJumpTimestamp] = useState("");
  const [selectedEvent, setSelectedEvent] = useState<PlatformEvent | null>(null);

  const { data: fetchedData } = useQuery({
    queryKey: ["/admin/events", "timeline", filterDomain, filterType, filterActor],
    refetchInterval: 10000,
    retry: false,
    queryFn: () => socialApi.getEvents({
      domain: filterDomain || undefined,
      event_type: filterType || undefined,
      actor_id: filterActor || undefined,
      limit: 200,
    }),
  });

  const allEvents = useMemo(() => {
    const fetched = (fetchedData?.events ?? []) as PlatformEvent[];
    const combined = new Map<string, PlatformEvent>();
    for (const e of fetched) combined.set(e.event_id, e);
    for (const e of storeEvents) combined.set(e.event_id, e);
    return Array.from(combined.values()).sort((a, b) =>
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );
  }, [fetchedData, storeEvents]);

  const filteredEvents = useMemo(() => {
    return allEvents.filter((e) => {
      if (filterDomain && e.domain !== filterDomain) return false;
      if (filterType && !e.event_type.includes(filterType)) return false;
      if (filterActor && !e.actor_id.includes(filterActor)) return false;
      return true;
    });
  }, [allEvents, filterDomain, filterType, filterActor]);

  const cursorIndex = Math.max(0, Math.floor((sliderPos / 100) * filteredEvents.length) - 1);
  const visibleEvents = filteredEvents.slice(0, cursorIndex + 1);
  const currentEvent = filteredEvents[cursorIndex] ?? null;

  const replayState = useMemo(() => {
    return reconstructState(visibleEvents);
  }, [visibleEvents]);

  const handleJump = useCallback(() => {
    if (!jumpEventId.trim()) return;
    const idx = filteredEvents.findIndex((e) => e.event_id.startsWith(jumpEventId.trim()));
    if (idx >= 0) {
      setSliderPos(((idx + 1) / filteredEvents.length) * 100);
    }
  }, [jumpEventId, filteredEvents]);

  const handleJumpToTimestamp = useCallback(() => {
    if (!jumpTimestamp) return;
    const target = new Date(jumpTimestamp).getTime();
    if (isNaN(target)) return;
    let closest = 0;
    let minDiff = Infinity;
    for (let i = 0; i < filteredEvents.length; i++) {
      const diff = Math.abs(new Date(filteredEvents[i].timestamp).getTime() - target);
      if (diff < minDiff) { minDiff = diff; closest = i; }
    }
    setSliderPos(((closest + 1) / filteredEvents.length) * 100);
  }, [jumpTimestamp, filteredEvents]);

  const stepBack = useCallback(() => {
    setSliderPos((p) => Math.max(0, p - (100 / Math.max(filteredEvents.length, 1))));
  }, [filteredEvents.length]);

  const stepForward = useCallback(() => {
    setSliderPos((p) => Math.min(100, p + (100 / Math.max(filteredEvents.length, 1))));
  }, [filteredEvents.length]);

  return (
    <div className="h-full flex flex-col overflow-hidden" data-testid="system-timeline">
      <div className="glass-panel border-b border-white/[0.06] px-4 py-3 space-y-3 shrink-0">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-3">
            <button onClick={stepBack} className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-white/[0.04] transition-colors" data-testid="btn-step-back">
              <Rewind className="w-4 h-4" />
            </button>
            <input
              type="range"
              min={0}
              max={100}
              step={0.1}
              value={sliderPos}
              onChange={(e) => setSliderPos(Number(e.target.value))}
              className="w-64 accent-primary"
              data-testid="timeline-slider"
            />
            <button onClick={stepForward} className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-white/[0.04] transition-colors" data-testid="btn-step-forward">
              <FastForward className="w-4 h-4" />
            </button>
          </div>

          <span className="text-[10px] font-mono text-muted-foreground" data-testid="timeline-position">
            {visibleEvents.length} / {filteredEvents.length} events
          </span>

          {currentEvent && (
            <span className="text-[10px] font-mono text-signal-blue" data-testid="timeline-current-time">
              {new Date(currentEvent.timestamp).toLocaleString()}
            </span>
          )}

          <div className="ml-auto flex items-center gap-2">
            <input
              value={jumpEventId}
              onChange={(e) => setJumpEventId(e.target.value)}
              placeholder="Jump to event ID..."
              className="bg-background border border-white/[0.1] rounded-md px-2 py-1 text-[10px] font-mono text-foreground w-36"
              data-testid="input-jump-event"
            />
            <button onClick={handleJump} className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-white/[0.04]" data-testid="btn-jump">
              <Search className="w-3.5 h-3.5" />
            </button>
            <input
              type="datetime-local"
              value={jumpTimestamp}
              onChange={(e) => setJumpTimestamp(e.target.value)}
              className="bg-background border border-white/[0.1] rounded-md px-2 py-1 text-[10px] font-mono text-foreground"
              data-testid="input-jump-timestamp"
            />
            <button onClick={handleJumpToTimestamp} className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-white/[0.04]" data-testid="btn-jump-timestamp">
              <Clock className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        <div className="relative h-12 rounded-lg bg-white/[0.02] border border-white/[0.06] overflow-hidden" data-testid="timeline-track">
          {filteredEvents.map((event, i) => {
            const pos = ((i + 1) / filteredEvents.length) * 100;
            const isError = isErrorEvent(event);
            return (
              <button
                key={event.event_id}
                onClick={() => {
                  setSliderPos(pos);
                  setSelectedEvent(event);
                }}
                className={cn(
                  "absolute top-1/2 -translate-y-1/2 w-2 h-2 rounded-full transition-transform hover:scale-150",
                  isError ? "bg-signal-red" : (DOMAIN_COLORS[event.domain] || "bg-signal-blue"),
                  i <= cursorIndex ? "opacity-100" : "opacity-30"
                )}
                style={{ left: `${pos}%` }}
                data-testid={`timeline-node-${i}`}
              />
            );
          })}
          <div
            className="absolute top-0 bottom-0 left-0 bg-signal-blue/10 pointer-events-none"
            style={{ width: `${sliderPos}%` }}
          />
        </div>

        <div className="flex flex-wrap gap-3">
          <div className="space-y-1">
            <label className="mono-label text-[9px]">Domain</label>
            <select
              value={filterDomain}
              onChange={(e) => setFilterDomain(e.target.value)}
              className="bg-background border border-white/[0.1] rounded-md px-2 py-1 text-[10px] font-mono text-foreground"
              data-testid="filter-timeline-domain"
            >
              <option value="">All</option>
              <option value="content">Content</option>
              <option value="trust">Trust</option>
              <option value="governance">Governance</option>
              <option value="workers">Workers</option>
              <option value="platform">Platform</option>
              <option value="feed_policy">Feed Policy</option>
            </select>
          </div>
          <div className="space-y-1">
            <label className="mono-label text-[9px]">Event Type</label>
            <input
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              placeholder="e.g. content_created"
              className="bg-background border border-white/[0.1] rounded-md px-2 py-1 text-[10px] font-mono text-foreground w-36"
              data-testid="filter-timeline-type"
            />
          </div>
          <div className="space-y-1">
            <label className="mono-label text-[9px]">Actor</label>
            <input
              value={filterActor}
              onChange={(e) => setFilterActor(e.target.value)}
              placeholder="Actor ID"
              className="bg-background border border-white/[0.1] rounded-md px-2 py-1 text-[10px] font-mono text-foreground w-36"
              data-testid="filter-timeline-actor"
            />
          </div>
          <div className="flex items-end gap-2">
            {["content", "trust", "governance", "workers"].map((d) => (
              <div key={d} className="flex items-center gap-1 text-[9px] text-muted-foreground">
                <div className={cn("w-2 h-2 rounded-full", DOMAIN_COLORS[d])} />
                <span>{d}</span>
              </div>
            ))}
            <div className="flex items-center gap-1 text-[9px] text-muted-foreground">
              <div className="w-2 h-2 rounded-full bg-signal-red" />
              <span>error</span>
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-4 gap-3 p-4 overflow-y-auto">
        <GlassCard variant="elevated">
          <GlassCardHeader>
            <GlassCardTitle><Rss className="w-3 h-3 inline mr-1 text-signal-blue" />Feed State</GlassCardTitle>
          </GlassCardHeader>
          <GlassCardBody className="space-y-2">
            <MetricRow className="flex-col items-start">
              <Metric label="Total Posts" value={replayState.feed.totalPosts} signal="blue" data-testid="replay-feed-posts" />
              <Metric label="Policy Version" value={replayState.feed.lastPolicyVersion || "default"} data-testid="replay-feed-policy" />
            </MetricRow>
            {replayState.feed.recentPosts.length > 0 && (
              <div className="space-y-1">
                <span className="mono-label text-[9px]">Recent Posts</span>
                {replayState.feed.recentPosts.slice(-3).map((p, i) => (
                  <div key={i} className="text-[10px] font-mono text-muted-foreground truncate">
                    {p.author_id.slice(0, 12)} — {new Date(p.timestamp).toLocaleTimeString()}
                  </div>
                ))}
              </div>
            )}
          </GlassCardBody>
        </GlassCard>

        <GlassCard variant="elevated">
          <GlassCardHeader>
            <GlassCardTitle><Users className="w-3 h-3 inline mr-1 text-signal-green" />Trust State</GlassCardTitle>
          </GlassCardHeader>
          <GlassCardBody className="space-y-2">
            <MetricRow className="flex-col items-start">
              <Metric label="Users" value={replayState.trust.totalUsers} signal="green" data-testid="replay-trust-users" />
              <Metric label="Updates" value={replayState.trust.trustUpdates} data-testid="replay-trust-updates" />
              <Metric label="Avg Score" value={replayState.trust.averageTrust.toFixed(1)} data-testid="replay-trust-avg" />
            </MetricRow>
            {replayState.trust.topActors.length > 0 && (
              <div className="space-y-1">
                <span className="mono-label text-[9px]">Top Actors</span>
                {replayState.trust.topActors.map((a, i) => (
                  <div key={i} className="text-[10px] font-mono text-muted-foreground">
                    {a.actor_id.slice(0, 12)} — {a.score}
                  </div>
                ))}
              </div>
            )}
          </GlassCardBody>
        </GlassCard>

        <GlassCard variant="elevated">
          <GlassCardHeader>
            <GlassCardTitle><Shield className="w-3 h-3 inline mr-1 text-signal-purple" />Governance State</GlassCardTitle>
          </GlassCardHeader>
          <GlassCardBody>
            <MetricRow className="flex-col items-start">
              <Metric label="Proposals" value={replayState.governance.totalProposals} signal="purple" data-testid="replay-gov-proposals" />
              <Metric label="Approved" value={replayState.governance.approvedProposals} signal="green" data-testid="replay-gov-approved" />
              <Metric label="Rejected" value={replayState.governance.rejectedProposals} signal="red" data-testid="replay-gov-rejected" />
              <Metric label="Policy Changes" value={replayState.governance.policyChanges} signal="amber" data-testid="replay-gov-changes" />
            </MetricRow>
          </GlassCardBody>
        </GlassCard>

        <GlassCard variant="elevated">
          <GlassCardHeader>
            <GlassCardTitle><Server className="w-3 h-3 inline mr-1 text-signal-amber" />Worker State</GlassCardTitle>
          </GlassCardHeader>
          <GlassCardBody>
            <MetricRow className="flex-col items-start">
              <Metric label="Heartbeats" value={replayState.workers.heartbeatCount} signal="amber" data-testid="replay-worker-hb" />
              <Metric label="Active Workers" value={replayState.workers.activeWorkers.size} signal="green" data-testid="replay-worker-active" />
              <Metric label="Publishes" value={replayState.workers.publishEvents} signal="blue" data-testid="replay-worker-pub" />
              <Metric label="Failures" value={replayState.workers.failedPublishes} signal={replayState.workers.failedPublishes > 0 ? "red" : "default"} data-testid="replay-worker-fail" />
            </MetricRow>
          </GlassCardBody>
        </GlassCard>
      </div>

      <GlassModal
        open={!!selectedEvent}
        onClose={() => setSelectedEvent(null)}
        title="Timeline Event Detail"
        size="md"
        data-testid="timeline-event-modal"
      >
        {selectedEvent && (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="glass-inset rounded-md px-3 py-2">
                <span className="mono-label">Event ID</span>
                <p className="font-mono text-foreground mt-0.5 break-all">{selectedEvent.event_id}</p>
              </div>
              <div className="glass-inset rounded-md px-3 py-2">
                <span className="mono-label">Domain</span>
                <p className={cn("font-mono mt-0.5", DOMAIN_DOT_COLORS[selectedEvent.domain] || "text-foreground")}>{selectedEvent.domain}</p>
              </div>
              <div className="glass-inset rounded-md px-3 py-2">
                <span className="mono-label">Type</span>
                <p className="font-mono text-foreground mt-0.5">{selectedEvent.event_type}</p>
              </div>
              <div className="glass-inset rounded-md px-3 py-2">
                <span className="mono-label">Actor</span>
                <p className="font-mono text-foreground mt-0.5 break-all">{selectedEvent.actor_id}</p>
              </div>
            </div>
            <div>
              <span className="mono-label">Payload</span>
              <pre className="mt-1 glass-inset rounded-md p-3 text-[11px] font-mono text-foreground overflow-auto max-h-[200px]">
                {JSON.stringify(selectedEvent.payload, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </GlassModal>
    </div>
  );
}
