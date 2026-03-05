import { useState, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "wouter";
import { socialApi, type EventRecord } from "@/services/api";
import { GlassCard, GlassCardHeader, GlassCardTitle, GlassCardBody } from "@/components/common/Card";
import { GlassModal } from "@/components/common/Modal";
import { Metric, MetricRow } from "@/components/common/Metric";
import { cn } from "@/lib/utils";
import { ArrowLeft, Activity, Search, Filter, Command, ChevronLeft, ChevronRight } from "lucide-react";
import { useUIState } from "@/store/uiState";

const DOMAINS = ["", "content", "trust", "governance", "platform", "feed_policy"];

const domainDotClass: Record<string, string> = {
  content: "signal-dot-blue",
  trust: "signal-dot-green",
  governance: "signal-dot-purple",
  platform: "signal-dot-amber",
  feed_policy: "signal-dot-purple",
};

export default function EventExplorer() {
  const { openPalette } = useUIState();
  const [domain, setDomain] = useState("");
  const [eventType, setEventType] = useState("");
  const [actorId, setActorId] = useState("");
  const [offset, setOffset] = useState(0);
  const [inspecting, setInspecting] = useState<EventRecord | null>(null);
  const limit = 25;

  const { data, isLoading } = useQuery({
    queryKey: ["/admin/events", domain, eventType, actorId, offset],
    refetchInterval: 10000,
    retry: false,
    queryFn: () =>
      socialApi.getEvents({
        domain: domain || undefined,
        event_type: eventType || undefined,
        actor_id: actorId || undefined,
        limit,
        offset,
      }),
  });

  const events = data?.events ?? [];
  const total = data?.total ?? 0;

  const handleSelect = useCallback((e: EventRecord) => setInspecting(e), []);
  const handleClose = useCallback(() => setInspecting(null), []);

  return (
    <div className="min-h-screen bg-background flex flex-col" data-testid="event-explorer">
      <header className="glass-panel border-b border-white/[0.06] px-4 py-2 flex items-center gap-3 shrink-0">
        <Link href="/" className="p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-white/[0.04] transition-colors" data-testid="nav-back">
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <Activity className="w-4 h-4 text-chart-1" />
        <span className="font-mono text-sm font-bold tracking-tight text-foreground">EVENT EXPLORER</span>
        <button onClick={openPalette} className="ml-auto flex items-center gap-1 px-2 py-1 rounded-md text-xs text-muted-foreground hover:text-foreground hover:bg-white/[0.04]" data-testid="btn-palette">
          <Command className="w-3 h-3" />K
        </button>
      </header>

      <main className="flex-1 p-4 overflow-y-auto">
        <MetricRow className="mb-4">
          <Metric label="Total Events" value={total} signal="blue" data-testid="metric-total-events" />
          <Metric label="Showing" value={events.length} data-testid="metric-showing" />
          <Metric label="Page" value={Math.floor(offset / limit) + 1} data-testid="metric-page" />
        </MetricRow>

        <GlassCard className="mb-4">
          <GlassCardHeader>
            <GlassCardTitle><Filter className="w-3 h-3 inline mr-1" />Filters</GlassCardTitle>
          </GlassCardHeader>
          <GlassCardBody>
            <div className="flex flex-wrap gap-3">
              <div className="space-y-1">
                <label className="mono-label text-[10px]">Domain</label>
                <select
                  value={domain}
                  onChange={(e) => { setDomain(e.target.value); setOffset(0); }}
                  className="bg-background border border-white/[0.1] rounded-md px-2 py-1 text-xs font-mono text-foreground"
                  data-testid="filter-domain"
                >
                  <option value="">All</option>
                  {DOMAINS.filter(Boolean).map((d) => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
              </div>
              <div className="space-y-1">
                <label className="mono-label text-[10px]">Event Type</label>
                <input
                  value={eventType}
                  onChange={(e) => { setEventType(e.target.value); setOffset(0); }}
                  placeholder="e.g. content_created"
                  className="bg-background border border-white/[0.1] rounded-md px-2 py-1 text-xs font-mono text-foreground w-40"
                  data-testid="filter-event-type"
                />
              </div>
              <div className="space-y-1">
                <label className="mono-label text-[10px]">Actor ID</label>
                <input
                  value={actorId}
                  onChange={(e) => { setActorId(e.target.value); setOffset(0); }}
                  placeholder="UUID"
                  className="bg-background border border-white/[0.1] rounded-md px-2 py-1 text-xs font-mono text-foreground w-56"
                  data-testid="filter-actor-id"
                />
              </div>
            </div>
          </GlassCardBody>
        </GlassCard>

        <GlassCard variant="elevated">
          <GlassCardHeader>
            <GlassCardTitle>Events</GlassCardTitle>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setOffset(Math.max(0, offset - limit))}
                disabled={offset === 0}
                className="p-1 rounded-md text-muted-foreground hover:text-foreground disabled:opacity-30"
                data-testid="btn-prev-page"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                onClick={() => setOffset(offset + limit)}
                disabled={events.length < limit}
                className="p-1 rounded-md text-muted-foreground hover:text-foreground disabled:opacity-30"
                data-testid="btn-next-page"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </GlassCardHeader>
          <GlassCardBody className="p-0">
            {isLoading ? (
              <div className="text-xs text-muted-foreground text-center py-8">Loading events...</div>
            ) : events.length === 0 ? (
              <div className="text-xs text-muted-foreground text-center py-8" data-testid="events-empty">No events found</div>
            ) : (
              <div className="divide-y divide-white/[0.04]">
                {events.map((ev) => (
                  <button
                    key={ev.event_id}
                    onClick={() => handleSelect(ev)}
                    className="w-full flex items-center gap-3 px-4 py-2.5 text-left hover:bg-white/[0.03] transition-colors"
                    data-testid={`event-row-${ev.event_id}`}
                  >
                    <div className={cn("signal-dot shrink-0", domainDotClass[ev.domain] || "signal-dot-blue")} />
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-mono text-foreground">{ev.event_type}</div>
                      <div className="text-[10px] font-mono text-muted-foreground truncate">
                        {ev.actor_id.slice(0, 12)} &middot; {new Date(ev.timestamp).toLocaleString()}
                      </div>
                    </div>
                    <span className="mono-label text-[9px]">{ev.domain}</span>
                  </button>
                ))}
              </div>
            )}
          </GlassCardBody>
        </GlassCard>
      </main>

      <GlassModal open={!!inspecting} onClose={handleClose} title="Event Detail" size="lg" data-testid="event-detail-modal">
        {inspecting && (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="glass-inset rounded-md px-3 py-2">
                <span className="mono-label">Event ID</span>
                <p className="font-mono text-foreground mt-0.5 break-all">{inspecting.event_id}</p>
              </div>
              <div className="glass-inset rounded-md px-3 py-2">
                <span className="mono-label">Domain</span>
                <p className="font-mono text-foreground mt-0.5">{inspecting.domain}</p>
              </div>
              <div className="glass-inset rounded-md px-3 py-2">
                <span className="mono-label">Event Type</span>
                <p className="font-mono text-foreground mt-0.5">{inspecting.event_type}</p>
              </div>
              <div className="glass-inset rounded-md px-3 py-2">
                <span className="mono-label">Actor ID</span>
                <p className="font-mono text-foreground mt-0.5 break-all">{inspecting.actor_id}</p>
              </div>
            </div>
            <div>
              <span className="mono-label">Payload</span>
              <pre className="mt-1 glass-inset rounded-md p-3 text-[11px] font-mono text-foreground overflow-auto max-h-[300px]" data-testid="event-payload-json">
                {JSON.stringify(inspecting.payload, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </GlassModal>
    </div>
  );
}
