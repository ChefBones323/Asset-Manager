import { Badge } from "@/components/ui/badge";
import type { JobStatus } from "@shared/schema";
import { Clock, CheckCircle, Play, XCircle, FileCheck, FileText, Ban, Pause, ShieldAlert } from "lucide-react";

const statusConfig: Record<
  string,
  { label: string; variant: "default" | "secondary" | "destructive" | "outline"; icon: typeof Clock; className?: string }
> = {
  draft: { label: "Draft", variant: "secondary", icon: FileText },
  awaiting_approval: { label: "Awaiting Approval", variant: "outline", icon: Clock },
  approved: { label: "Approved", variant: "default", icon: FileCheck },
  running: { label: "Running", variant: "default", icon: Play },
  paused: { label: "Paused", variant: "outline", icon: Pause, className: "border-yellow-500/50 text-yellow-600 dark:text-yellow-400 bg-yellow-500/10" },
  escalated: { label: "Escalated", variant: "outline", icon: ShieldAlert, className: "border-orange-500/50 text-orange-600 dark:text-orange-400 bg-orange-500/10" },
  completed: { label: "Completed", variant: "secondary", icon: CheckCircle },
  failed: { label: "Failed", variant: "destructive", icon: XCircle },
  cancelled: { label: "Cancelled", variant: "outline", icon: Ban },
};

export function StatusBadge({ status }: { status: JobStatus | null }) {
  const config = statusConfig[status || "draft"] || statusConfig.draft;
  const Icon = config.icon;

  return (
    <Badge variant={config.variant} className={config.className} data-testid={`badge-status-${status}`}>
      <Icon className="w-3 h-3 mr-1" />
      {config.label}
    </Badge>
  );
}
