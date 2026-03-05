import { memo } from "react";
import { useQuery } from "@tanstack/react-query";
import { socialApi, type WorkerData } from "@/services/api";
import { GlassCard, GlassCardHeader, GlassCardTitle, GlassCardBody } from "@/components/common/Card";
import { Metric } from "@/components/common/Metric";
import { cn } from "@/lib/utils";
import { Server, Clock, AlertTriangle, Inbox } from "lucide-react";

function heartbeatStatus(lastBeat?: string): "green" | "amber" | "red" {
  if (!lastBeat) return "red";
  const diff = Date.now() - new Date(lastBeat).getTime();
  if (diff < 15000) return "green";
  if (diff < 30000) return "amber";
  return "red";
}

const dotColor: Record<string, string> = {
  green: "signal-dot-green",
  amber: "signal-dot-amber",
  red: "signal-dot-red",
};

const WorkerCard = memo(function WorkerCard({ worker, lease }: {
  worker: WorkerData["workers"][0];
  lease?: WorkerData["active_leases"][0];
}) {
  const beat = heartbeatStatus(worker.last_heartbeat);
  return (
    <div className="glass-inset rounded-md px-3 py-2 space-y-1" data-testid={`worker-card-${worker.worker_id}`}>
      <div className="flex items-center gap-2">
        <div className={cn("signal-dot shrink-0", dotColor[beat])} />
        <span className="font-mono text-xs text-foreground truncate">{worker.worker_id.slice(0, 12)}</span>
        <span className={cn("ml-auto mono-label text-[9px]", worker.status === "active" ? "text-signal-green" : "text-muted-foreground")}>
          {worker.status}
        </span>
      </div>
      {lease && (
        <div className="flex items-center gap-1 text-[10px] font-mono text-muted-foreground">
          <Clock className="w-3 h-3" />
          <span>Job: {lease.job_id.slice(0, 8)}</span>
          <span className="ml-auto">exp: {new Date(lease.expires_at).toLocaleTimeString("en-US", { hour12: false })}</span>
        </div>
      )}
      <div className="flex items-center gap-2 text-[10px] font-mono text-muted-foreground">
        <span>{worker.jobs_processed} jobs</span>
      </div>
    </div>
  );
});

export const InfrastructurePanel = memo(function InfrastructurePanel({ className }: { className?: string }) {
  const { data, isLoading } = useQuery<WorkerData>({
    queryKey: ["/admin/workers"],
    refetchInterval: 5000,
    retry: false,
    queryFn: async () => socialApi.getWorkers(),
  });

  const workers = data?.workers ?? [];
  const leases = data?.active_leases ?? [];
  const dlq = data?.dead_letter_queue ?? [];

  return (
    <div className={cn("flex flex-col gap-3 h-full", className)} data-testid="infrastructure-panel">
      <div className="flex items-center gap-2 px-1">
        <Server className="w-4 h-4 text-signal-amber" />
        <span className="mono-label">Infrastructure</span>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <Metric label="Workers" value={workers.length} signal={workers.length > 0 ? "green" : "default"} data-testid="metric-workers" />
        <Metric label="Leases" value={leases.length} signal={leases.length > 0 ? "amber" : "default"} data-testid="metric-leases" />
        <Metric label="DLQ" value={dlq.length} signal={dlq.length > 0 ? "red" : "default"} data-testid="metric-dlq" />
        <Metric label="Total Leases" value={data?.total_leases ?? 0} data-testid="metric-total-leases" />
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
              <WorkerCard
                key={w.worker_id}
                worker={w}
                lease={leases.find((l) => l.worker_id === w.worker_id)}
              />
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
            {dlq.map((d, i) => (
              <div key={i} className="glass-inset rounded px-2 py-1 text-[10px] font-mono" data-testid={`dlq-item-${i}`}>
                <span className="text-signal-red">{d.job_id.slice(0, 8)}</span>
                <span className="text-muted-foreground ml-2">retries: {d.retry_count}</span>
                <span className="text-muted-foreground ml-2 truncate">{d.reason}</span>
              </div>
            ))}
          </GlassCardBody>
        </GlassCard>
      )}
    </div>
  );
});
