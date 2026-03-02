import { Badge } from "@/components/ui/badge";
import type { JobStatus } from "@shared/schema";
import { Clock, CheckCircle, Play, XCircle, FileCheck, FileText } from "lucide-react";

const statusConfig: Record<
  string,
  { label: string; variant: "default" | "secondary" | "destructive" | "outline"; icon: typeof Clock }
> = {
  draft: { label: "Draft", variant: "secondary", icon: FileText },
  awaiting_approval: { label: "Awaiting Approval", variant: "outline", icon: Clock },
  approved: { label: "Approved", variant: "default", icon: FileCheck },
  running: { label: "Running", variant: "default", icon: Play },
  completed: { label: "Completed", variant: "secondary", icon: CheckCircle },
  failed: { label: "Failed", variant: "destructive", icon: XCircle },
};

export function StatusBadge({ status }: { status: JobStatus | null }) {
  const config = statusConfig[status || "draft"] || statusConfig.draft;
  const Icon = config.icon;

  return (
    <Badge variant={config.variant} data-testid={`badge-status-${status}`}>
      <Icon className="w-3 h-3 mr-1" />
      {config.label}
    </Badge>
  );
}
