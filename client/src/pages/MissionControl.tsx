import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "wouter";
import { socialApi, type EventMetrics } from "@/services/api";
import { useEventStore } from "@/store/eventStore";
import { connectEventStream, disconnectEventStream, isConnected } from "@/services/websocket";
import { InfrastructurePanel } from "@/components/workers/InfrastructurePanel";
import { EventPulsePanel } from "@/components/events/EventPulsePanel";
import { VerifiedPostCard, type PostData } from "@/components/feed/VerifiedPostCard";
import { Metric, MetricRow } from "@/components/common/Metric";
import { GlassCard, GlassCardHeader, GlassCardTitle, GlassCardBody } from "@/components/common/Card";
import { cn } from "@/lib/utils";
import {
  Activity, Shield, Rss, Users, BarChart3, Search,
  Wifi, WifiOff, LogOut, Command,
} from "lucide-react";
import { useUIState } from "@/store/uiState";
import { useAuth } from "@/hooks/use-auth";

const NAV_LINKS = [
  { path: "/governance", label: "Governance", icon: Shield },
  { path: "/feed-debugger", label: "Feed Debugger", icon: BarChart3 },
  { path: "/trust-graph", label: "Trust Graph", icon: Users },
  { path: "/events", label: "Event Explorer", icon: Activity },
];

const MOCK_FEED: PostData[] = [
  {
    content_id: "demo-001",
    author_id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    author_name: "CivicReporter",
    trust_score: 82,
    content: "New governance proposal submitted: Increase trust weight in feed ranking from 0.20 to 0.30 for community-sourced content.",
    reaction_count: 14,
    comment_count: 3,
    timestamp: new Date(Date.now() - 120000).toISOString(),
    event_id: "evt-f7a3b2c1-demo",
    manifest_id: "mfst-98765-demo",
    policy_version: "CivicBalanced_v3",
  },
  {
    content_id: "demo-002",
    author_id: "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    author_name: "InfraOps",
    trust_score: 65,
    content: "Worker pool scaled to 12 nodes. Queue depth nominal. All projections current.",
    reaction_count: 8,
    timestamp: new Date(Date.now() - 300000).toISOString(),
    event_id: "evt-d4e5f6a7-demo",
    manifest_id: "mfst-54321-demo",
    policy_version: "CivicBalanced_v3",
  },
  {
    content_id: "demo-003",
    author_id: "c3d4e5f6-a7b8-9012-cdef-123456789012",
    author_name: "TrustAnalyst",
    trust_score: 28,
    content: "Trust delegation chain detected between 4 accounts. Loop prevention engaged at depth 3. Manual review recommended.",
    reaction_count: 2,
    comment_count: 7,
    timestamp: new Date(Date.now() - 900000).toISOString(),
  },
];

export default function MissionControl() {
  const { openPalette } = useUIState();
  const { logout } = useAuth();
  const events = useEventStore((s) => s.events);

  const { data: metrics } = useQuery<EventMetrics>({
    queryKey: ["/admin/event_metrics"],
    refetchInterval: 5000,
    retry: false,
    queryFn: async () => socialApi.getEventMetrics(),
  });

  useEffect(() => {
    connectEventStream();
    return () => disconnectEventStream();
  }, []);

  const connected = isConnected();

  return (
    <div className="min-h-screen bg-background flex flex-col" data-testid="mission-control">
      <header className="glass-panel border-b border-white/[0.06] px-4 py-2 flex items-center gap-4 shrink-0" data-testid="system-top-bar">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-signal-blue animate-pulse-glow" />
          <span className="font-mono text-sm font-bold tracking-tight text-foreground">CIVIC MISSION CONTROL</span>
        </div>

        <div className="flex items-center gap-3 ml-4 mr-auto">
          {NAV_LINKS.map(({ path, label, icon: Icon }) => (
            <Link key={path} href={path} className="flex items-center gap-1.5 px-2 py-1 rounded-md text-xs text-muted-foreground hover:text-foreground hover:bg-white/[0.04] transition-colors" data-testid={`nav-${label.toLowerCase().replace(/\s/g, "-")}`}>
              <Icon className="w-3.5 h-3.5" />
              <span className="hidden md:inline">{label}</span>
            </Link>
          ))}
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-[10px] font-mono text-muted-foreground">
            {connected ? <Wifi className="w-3 h-3 text-signal-green" /> : <WifiOff className="w-3 h-3 text-signal-red" />}
            <span data-testid="status-connection">{connected ? "LIVE" : "OFFLINE"}</span>
          </div>
          <span className="font-mono text-[10px] text-muted-foreground" data-testid="status-event-rate">
            {(metrics?.events_per_second ?? 0).toFixed(1)}/s
          </span>
          <button onClick={openPalette} className="flex items-center gap-1 px-2 py-1 rounded-md text-xs text-muted-foreground hover:text-foreground hover:bg-white/[0.04] transition-colors" data-testid="btn-open-palette">
            <Command className="w-3 h-3" /><span className="hidden md:inline">K</span>
          </button>
          <button onClick={() => logout()} className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-white/[0.04] transition-colors" data-testid="btn-logout">
            <LogOut className="w-3.5 h-3.5" />
          </button>
        </div>
      </header>

      <main className="flex-1 grid grid-cols-1 lg:grid-cols-[280px_1fr_300px] gap-0 min-h-0 overflow-hidden">
        <div className="glass-panel border-r border-white/[0.06] p-3 overflow-y-auto hidden lg:block">
          <InfrastructurePanel />
        </div>

        <div className="p-4 overflow-y-auto">
          <div className="flex items-center gap-2 mb-4">
            <Rss className="w-4 h-4 text-signal-blue" />
            <span className="mono-label">Verified Civic Feed</span>
          </div>
          <div className="space-y-3 max-w-2xl" data-testid="civic-feed">
            {MOCK_FEED.map((post) => (
              <VerifiedPostCard key={post.content_id} post={post} />
            ))}
          </div>
        </div>

        <div className="glass-panel border-l border-white/[0.06] hidden lg:flex flex-col min-h-0">
          <EventPulsePanel />
        </div>
      </main>

      <footer className="glass-panel border-t border-white/[0.06] px-4 py-2 shrink-0" data-testid="status-bar">
        <MetricRow className="justify-center">
          <Metric label="Event Rate" value={(metrics?.events_per_second ?? 0).toFixed(1)} unit="/s" signal="blue" data-testid="status-metric-rate" />
          <Metric label="Workers" value={metrics?.queue_depth !== undefined ? "active" : "--"} signal="green" data-testid="status-metric-workers" />
          <Metric label="Queue" value={metrics?.queue_depth ?? 0} signal={metrics && metrics.queue_depth > 10 ? "amber" : "default"} data-testid="status-metric-queue" />
          <Metric label="Retry Rate" value={((metrics?.retry_rate ?? 0) * 100).toFixed(2)} unit="%" signal={metrics && metrics.retry_rate > 0.01 ? "red" : "default"} data-testid="status-metric-retry" />
          <Metric label="DLQ" value={metrics?.dead_letter_count ?? 0} signal={metrics && metrics.dead_letter_count > 0 ? "red" : "default"} data-testid="status-metric-dlq" />
        </MetricRow>
      </footer>
    </div>
  );
}
