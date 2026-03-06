import { useEffect } from "react";
import { useLocation } from "wouter";
import { NavigationRail } from "./NavigationRail";
import { SystemTopBar } from "./SystemTopBar";
import { useUIState } from "@/store/uiState";
import { connectEventStream, disconnectEventStream } from "@/services/websocket";
import { startSocialPublisherWorker, stopSocialPublisherWorker } from "@/workers/socialPublisherWorker";
import { Metric, MetricRow } from "@/components/common/Metric";
import { useQuery } from "@tanstack/react-query";
import { socialApi, type EventMetrics } from "@/services/api";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [location] = useLocation();
  const { setActivePage } = useUIState();

  useEffect(() => {
    setActivePage(location);
  }, [location, setActivePage]);

  useEffect(() => {
    connectEventStream();
    startSocialPublisherWorker();
    return () => {
      disconnectEventStream();
      stopSocialPublisherWorker();
    };
  }, []);

  const { data: metrics } = useQuery<EventMetrics>({
    queryKey: ["/admin/event_metrics"],
    refetchInterval: 5000,
    retry: false,
    queryFn: async () => socialApi.getEventMetrics(),
  });

  return (
    <div className="h-screen bg-background flex overflow-hidden" data-testid="app-shell">
      <NavigationRail />

      <div className="flex-1 flex flex-col min-w-0">
        <SystemTopBar />

        <main className="flex-1 min-h-0 overflow-y-auto">
          {children}
        </main>

        <footer className="glass-panel border-t border-white/[0.06] px-4 py-1.5 shrink-0" data-testid="status-bar">
          <MetricRow className="justify-center">
            <Metric label="Event Rate" value={(metrics?.events_per_second ?? 0).toFixed(1)} unit="/s" signal="blue" data-testid="status-metric-rate" />
            <Metric label="Workers" value={metrics?.queue_depth !== undefined ? "active" : "--"} signal="green" data-testid="status-metric-workers" />
            <Metric label="Queue" value={metrics?.queue_depth ?? 0} signal={metrics && metrics.queue_depth > 10 ? "amber" : "default"} data-testid="status-metric-queue" />
            <Metric label="Retry Rate" value={((metrics?.retry_rate ?? 0) * 100).toFixed(2)} unit="%" signal={metrics && metrics.retry_rate > 0.01 ? "red" : "default"} data-testid="status-metric-retry" />
            <Metric label="DLQ" value={metrics?.dead_letter_count ?? 0} signal={metrics && metrics.dead_letter_count > 0 ? "red" : "default"} data-testid="status-metric-dlq" />
          </MetricRow>
        </footer>
      </div>
    </div>
  );
}
