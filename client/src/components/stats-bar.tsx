import type { Job } from "@shared/schema";
import { Clock, CheckCircle, Play, XCircle, FileCheck, Layers, Ban } from "lucide-react";

export function StatsBar({ jobs }: { jobs: Job[] }) {
  const counts = {
    total: jobs.length,
    awaiting: jobs.filter((j) => j.status === "awaiting_approval").length,
    approved: jobs.filter((j) => j.status === "approved").length,
    running: jobs.filter((j) => j.status === "running").length,
    completed: jobs.filter((j) => j.status === "completed").length,
    failed: jobs.filter((j) => j.status === "failed").length,
    cancelled: jobs.filter((j) => j.status === "cancelled").length,
  };

  const stats = [
    { label: "Total", value: counts.total, icon: Layers, color: "text-foreground" },
    { label: "Pending", value: counts.awaiting, icon: Clock, color: "text-chart-4" },
    { label: "Approved", value: counts.approved, icon: FileCheck, color: "text-primary" },
    { label: "Running", value: counts.running, icon: Play, color: "text-chart-2" },
    { label: "Completed", value: counts.completed, icon: CheckCircle, color: "text-chart-2" },
    { label: "Failed", value: counts.failed, icon: XCircle, color: "text-destructive" },
    { label: "Cancelled", value: counts.cancelled, icon: Ban, color: "text-muted-foreground" },
  ];

  return (
    <div className="grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-7 gap-3" data-testid="container-stats">
      {stats.map((stat) => {
        const Icon = stat.icon;
        return (
          <div
            key={stat.label}
            className="flex items-center gap-2 p-3 rounded-md bg-card border border-card-border"
            data-testid={`stat-${stat.label.toLowerCase()}`}
          >
            <Icon className={`w-4 h-4 ${stat.color} shrink-0`} />
            <div className="min-w-0">
              <p className="text-lg font-semibold leading-none">{stat.value}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{stat.label}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
