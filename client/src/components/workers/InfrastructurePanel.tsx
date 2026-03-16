import { memo } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchWorkers, fetchMetrics, type WorkersResponse, type MetricsData, type WorkerNodeData, type DLQEntry } from "@/services/workerApi";
import { GlassCard, GlassCardHeader, GlassCardTitle, GlassCardBody } from "@/components/common/Card";
import { Metric } from "@/components/common/Metric";
import { cn } from "@/lib/utils";
import { Server, Clock, AlertTriangle } from "lucide-react";

function heartbeatStatus(ageSec?: number | null): "green" | "amber" | "red" {
  if (ageSec == null) return "red";
  if (ageSec < 15) return "green";
  if (ageSec < 30) return "amber";
  return "red";
}

const dotColor: Record<string, string> = {
  green: "signal-dot-green",
  amber: "signal-dot-amber",
  red: "signal-dot-red",
};

const statusColor: Record<string, string> = {
  idle: "text-muted-foreground",
  busy: "text-signal-green",
  unhealthy: "text-signal-red",
};

const WorkerCard = memo(function WorkerCard({ worker }: { worker: WorkerNodeData }) {
  const beat = heartbeatStatus(worker.heartbeat_age_seconds);
  return (
    <div className="glass-inset rounded-md px-3 py-2 space-y-1" data-testid={`worker-card-${worker.id}`}>
      <div className="flex items-center gap-2">
        <div className={cn("signal-dot shrink-0", dotColor[beat])} />
        <span className="font-mono text-xs text-foreground truncate" data-testid={`worker-hostname-${worker.id}`}>{worker.hostname}</span>
        <span className={cn("ml-auto mono-label text-[9px]", statusColor[worker.status] || "text-muted-foreground")} data-testid={`worker-status-${worker.id}`}>
          {worker.status}
        </span>
      </div>
      {worker.current_job_id && (
        <div className="flex items-center gap-1 text-[10px] font-mono text-muted-foreground">
          <Clock className="w-3 h-3" />
          <span>Job: {worker.current_job_id.slice(0, 8)}</span>
        </div>
      )}
      <div className="flex items-center gap-2 text-[10px] font-mono text-muted-foreground">
        <span>{worker.capabilities.join(", ")}</span>
        {worker.heartbeat_age_seconds != null && (
          <span className="ml-auto">{Math.round(worker.heartbeat_age_seconds)}s ago</span>
        )}
      </div>
    </div>
  );
});

export const InfrastructurePanel = memo(function InfrastructurePanel({ className }: { className?: string }) {
  const { data: workersData, isLoading } = useQuery<WorkersResponse>({
    queryKey: ["/admin/workers"],
    refetchInterval: 5000,
    retry: false,
    queryFn: fetchWorkers,
  });

  const { data: metricsData } = useQuery<MetricsData>({
    queryKey: ["/metrics"],
    refetchInterval: 5000,
    retry: false,
    queryFn: fetchMetrics,
  });

  const workers = workersData?.workers ?? [];
  const queueDepth = workersData?.queue_depth;
  const dlq = workersData?.dead_letter_queue ?? [];

  return (
    <div className={cn("flex flex-col gap-3 h-full", className)} data-testid="infrastructure-panel">
      <div className="flex items-center gap-2 px-1">
        <Server className="w-4 h-4 text-signal-amber" />
        <span className="mono-label">Infrastructure</span>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <Metric
          label="Workers"
          value={metricsData?.active_workers ?? workers.length}
          signal={workers.length > 0 ? "green" : "default"}
          data-testid="metric-workers"
        />
        <Metric
          label="Busy"
          value={metricsData?.busy_workers ?? 0}
          signal={metricsData?.busy_workers ? "amber" : "default"}
          data-testid="metric-busy"
        />
        <Metric
          label="Queue"
          value={queueDepth?.queued ?? metricsData?.queue_depth ?? 0}
          signal={(queueDepth?.queued ?? 0) > 0 ? "amber" : "default"}
          data-testid="metric-queue"
        />
        <Metric
          label="DLQ"
          value={metricsData?.dlq_count ?? dlq.length}
          signal={(metricsData?.dlq_count ?? dlq.length) > 0 ? "red" : "default"}
          data-testid="metric-dlq"
        />
        <Metric
          label="Processed"
          value={metricsData?.jobs_processed_total ?? 0}
          data-testid="metric-processed"
        />
        <Metric
          label="Failed"
          value={metricsData?.jobs_failed_total ?? 0}
          signal={(metricsData?.jobs_failed_total ?? 0) > 0 ? "red" : "default"}
          data-testid="metric-failed"
        />
      </div>

      <GlassCard className="flex-1 min-h-0 overflow-hidden">
        <GlassCardHeader>
          <GlassCardTitle>Worker Registry</GlassCardTitle>
        </GlassCardHeader>
        <GlassCardBody className="overflow-y-auto max-h-[300px] space-y-2">
          {isLoading ? (
            <div className="text-xs text-muted-foreground text-center py-4">Loading workers...</div>
          ) : workers.length === 0 ? (
            <div className="text-xs text-muted-foreground text-center py-4" data-testid="workers-empty">No active workers</div>
          ) : (
            workers.map((w) => (
              <WorkerCard key={w.id} worker={w} />
            ))
          )}
        </GlassCardBody>
      </GlassCard>

      {dlq.length > 0 && (
        <GlassCard glow="red">
          <GlassCardHeader>
            <GlassCardTitle><AlertTriangle className="w-3 h-3 inline mr-1 text-signal-red" />Dead Letter Queue</GlassCardTitle>
          </GlassCardHeader>
          <GlassCardBody className="space-y-1 max-h-[150px] overflow-y-auto">
            {dlq.map((d) => (
              <div key={d.id} className="glass-inset rounded px-2 py-1 text-[10px] font-mono" data-testid={`dlq-item-${d.id}`}>
                <span className="text-signal-red">{d.job_id.slice(0, 8)}</span>
                <span className="text-muted-foreground ml-2 truncate">{d.error_message}</span>
              </div>
            ))}
          </GlassCardBody>
        </GlassCard>
      )}
    </div>
  );
});
