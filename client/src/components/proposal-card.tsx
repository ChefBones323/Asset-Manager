import { useMutation } from "@tanstack/react-query";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/status-badge";
import { useToast } from "@/hooks/use-toast";
import type { Job } from "@shared/schema";
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  FolderPlus,
  FolderEdit,
  Timer,
  Ban,
  Trash2,
  Pause,
  Play,
  ShieldAlert,
} from "lucide-react";

export function ProposalCard({ job }: { job: Job }) {
  const { toast } = useToast();

  const approveMutation = useMutation({
    mutationFn: () => apiRequest("POST", `/api/jobs/${job.id}/approve`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/jobs"] });
      toast({ title: "Job Approved", description: "Dispatched for execution." });
    },
    onError: () => {
      toast({ title: "Error", description: "Failed to approve job.", variant: "destructive" });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: () => apiRequest("POST", `/api/jobs/${job.id}/reject`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/jobs"] });
      toast({ title: "Job Rejected", description: "Proposal has been rejected." });
    },
    onError: () => {
      toast({ title: "Error", description: "Failed to reject job.", variant: "destructive" });
    },
  });

  const cancelMutation = useMutation({
    mutationFn: () => apiRequest("POST", `/api/jobs/${job.id}/cancel`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/jobs"] });
      toast({ title: "Job Cancelled", description: "Execution has been cancelled." });
    },
    onError: () => {
      toast({ title: "Error", description: "Failed to cancel job.", variant: "destructive" });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => apiRequest("POST", `/api/jobs/${job.id}/delete`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/jobs"] });
      toast({ title: "Job Deleted", description: "Record has been removed." });
    },
    onError: () => {
      toast({ title: "Error", description: "Failed to delete job.", variant: "destructive" });
    },
  });

  const pauseMutation = useMutation({
    mutationFn: () => apiRequest("POST", `/api/jobs/${job.id}/pause`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/jobs"] });
      toast({ title: "Job Paused", description: "Execution has been paused." });
    },
    onError: () => {
      toast({ title: "Error", description: "Failed to pause job.", variant: "destructive" });
    },
  });

  const resumeMutation = useMutation({
    mutationFn: () => apiRequest("POST", `/api/jobs/${job.id}/resume`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/jobs"] });
      toast({ title: "Job Resumed", description: "Execution has been resumed." });
    },
    onError: () => {
      toast({ title: "Error", description: "Failed to resume job.", variant: "destructive" });
    },
  });

  const escalateMutation = useMutation({
    mutationFn: () => apiRequest("POST", `/api/jobs/${job.id}/escalate`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/jobs"] });
      toast({ title: "Job Escalated", description: "Job has been escalated for review." });
    },
    onError: () => {
      toast({ title: "Error", description: "Failed to escalate job.", variant: "destructive" });
    },
  });

  const approveDestructiveMutation = useMutation({
    mutationFn: () => apiRequest("POST", `/api/jobs/${job.id}/approve-destructive`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/jobs"] });
      toast({ title: "Destructive Approved", description: "Destructive execution has been authorized." });
    },
    onError: () => {
      toast({ title: "Error", description: "Failed to approve destructive execution.", variant: "destructive" });
    },
  });

  const impact = job.impactAnalysis as {
    filesCreated: string[];
    filesModified: string[];
    destructiveChanges: boolean;
    estimatedTimeSeconds: number;
  } | null;

  const plan = job.proposedPlan as string[] | null;
  const isAwaitingApproval = job.status === "awaiting_approval";
  const needsDestructiveApproval = impact?.destructiveChanges && !job.destructiveApprovedAt;

  return (
    <Card data-testid={`card-job-${job.id}`}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <StatusBadge status={job.status} />
              {impact?.destructiveChanges && (
                <span className="inline-flex items-center gap-1 text-xs text-destructive font-medium">
                  <AlertTriangle className="w-3 h-3" />
                  {job.destructiveApprovedAt ? "Destructive (Approved)" : "Destructive"}
                </span>
              )}
            </div>
            <h3 className="font-medium text-sm leading-snug mt-2" data-testid={`text-intent-${job.id}`}>
              {job.intent}
            </h3>
          </div>
          <span className="text-xs text-muted-foreground whitespace-nowrap">
            {job.createdAt ? new Date(job.createdAt).toLocaleString() : ""}
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {job.reasoningSummary && (
          <div className="space-y-1.5">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Reasoning</p>
            <p className="text-sm text-foreground/80 leading-relaxed" data-testid={`text-reasoning-${job.id}`}>
              {job.reasoningSummary}
            </p>
          </div>
        )}

        {plan && plan.length > 0 && (
          <div className="space-y-1.5">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Execution Plan</p>
            <ol className="space-y-1">
              {plan.map((step, i) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <span className="text-xs font-mono text-primary mt-0.5 shrink-0">{String(i + 1).padStart(2, "0")}</span>
                  <span className="text-foreground/80">{step}</span>
                </li>
              ))}
            </ol>
          </div>
        )}

        {impact && (
          <div className="space-y-1.5">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Impact Analysis</p>
            <div className="grid grid-cols-2 gap-2">
              {impact.filesCreated.length > 0 && (
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <FolderPlus className="w-3.5 h-3.5 text-chart-2" />
                  <span>{impact.filesCreated.length} file(s) created</span>
                </div>
              )}
              {impact.filesModified.length > 0 && (
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <FolderEdit className="w-3.5 h-3.5 text-chart-4" />
                  <span>{impact.filesModified.length} file(s) modified</span>
                </div>
              )}
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <Timer className="w-3.5 h-3.5" />
                <span>~{impact.estimatedTimeSeconds}s</span>
              </div>
            </div>
            {(impact.filesCreated.length > 0 || impact.filesModified.length > 0) && (
              <div className="bg-muted/50 rounded-md p-2.5 mt-1.5">
                <pre className="text-xs font-mono text-muted-foreground whitespace-pre-wrap" data-testid={`text-files-${job.id}`}>
                  {[...impact.filesCreated.map((f) => `+ ${f}`), ...impact.filesModified.map((f) => `~ ${f}`)].join("\n")}
                </pre>
              </div>
            )}
          </div>
        )}

        {job.workerId && (job.status === "running" || job.status === "paused" || job.status === "escalated") && (
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span className="inline-flex items-center gap-1">
              <span className="font-medium">Worker:</span> {job.workerId}
            </span>
            {job.leaseExpiresAt && (
              <span className="inline-flex items-center gap-1">
                <span className="font-medium">Lease:</span> {new Date(job.leaseExpiresAt).toLocaleTimeString()}
              </span>
            )}
          </div>
        )}

        {job.logs && job.status !== "awaiting_approval" && (
          <div className="space-y-1.5">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Execution Logs</p>
            <div className="bg-background rounded-md p-3 max-h-40 overflow-y-auto">
              <pre className="text-xs font-mono text-chart-2 whitespace-pre-wrap" data-testid={`text-logs-${job.id}`}>
                {job.logs}
              </pre>
            </div>
          </div>
        )}

        {isAwaitingApproval && (
          <div className="flex items-center gap-2 pt-1">
            <Button
              onClick={() => approveMutation.mutate()}
              disabled={approveMutation.isPending}
              size="sm"
              data-testid={`button-approve-${job.id}`}
            >
              <CheckCircle className="w-3.5 h-3.5 mr-1" />
              Approve & Dispatch
            </Button>
            <Button
              onClick={() => rejectMutation.mutate()}
              disabled={rejectMutation.isPending}
              variant="destructive"
              size="sm"
              data-testid={`button-reject-${job.id}`}
            >
              <XCircle className="w-3.5 h-3.5 mr-1" />
              Reject
            </Button>
          </div>
        )}

        {job.status === "running" && (
          <div className="flex items-center gap-2 pt-1">
            <Button
              onClick={() => pauseMutation.mutate()}
              disabled={pauseMutation.isPending}
              variant="secondary"
              size="sm"
              data-testid={`button-pause-${job.id}`}
            >
              <Pause className="w-3.5 h-3.5 mr-1" />
              Pause
            </Button>
            <Button
              onClick={() => escalateMutation.mutate()}
              disabled={escalateMutation.isPending}
              variant="outline"
              size="sm"
              data-testid={`button-escalate-${job.id}`}
            >
              <ShieldAlert className="w-3.5 h-3.5 mr-1" />
              Escalate
            </Button>
            <Button
              onClick={() => cancelMutation.mutate()}
              disabled={cancelMutation.isPending}
              variant="destructive"
              size="sm"
              data-testid={`button-cancel-${job.id}`}
            >
              <Ban className="w-3.5 h-3.5 mr-1" />
              Cancel
            </Button>
          </div>
        )}

        {job.status === "paused" && (
          <div className="flex items-center gap-2 pt-1">
            <Button
              onClick={() => resumeMutation.mutate()}
              disabled={resumeMutation.isPending}
              size="sm"
              data-testid={`button-resume-${job.id}`}
            >
              <Play className="w-3.5 h-3.5 mr-1" />
              Resume
            </Button>
            <Button
              onClick={() => cancelMutation.mutate()}
              disabled={cancelMutation.isPending}
              variant="destructive"
              size="sm"
              data-testid={`button-cancel-${job.id}`}
            >
              <Ban className="w-3.5 h-3.5 mr-1" />
              Cancel
            </Button>
          </div>
        )}

        {job.status === "escalated" && (
          <div className="flex items-center gap-2 pt-1">
            {needsDestructiveApproval && (
              <Button
                onClick={() => approveDestructiveMutation.mutate()}
                disabled={approveDestructiveMutation.isPending}
                variant="outline"
                size="sm"
                className="border-orange-500/50 text-orange-600 dark:text-orange-400 hover:bg-orange-500/10"
                data-testid={`button-approve-destructive-${job.id}`}
              >
                <ShieldAlert className="w-3.5 h-3.5 mr-1" />
                Approve Destructive
              </Button>
            )}
            <Button
              onClick={() => resumeMutation.mutate()}
              disabled={resumeMutation.isPending}
              size="sm"
              data-testid={`button-resume-${job.id}`}
            >
              <Play className="w-3.5 h-3.5 mr-1" />
              Resume
            </Button>
            <Button
              onClick={() => cancelMutation.mutate()}
              disabled={cancelMutation.isPending}
              variant="destructive"
              size="sm"
              data-testid={`button-cancel-${job.id}`}
            >
              <Ban className="w-3.5 h-3.5 mr-1" />
              Cancel
            </Button>
          </div>
        )}

        {job.status === "approved" && (
          <div className="flex items-center gap-2 pt-1">
            <Button
              onClick={() => cancelMutation.mutate()}
              disabled={cancelMutation.isPending}
              variant="secondary"
              size="sm"
              data-testid={`button-cancel-${job.id}`}
            >
              <Ban className="w-3.5 h-3.5 mr-1" />
              Cancel
            </Button>
          </div>
        )}

        {(job.status === "completed" || job.status === "failed" || job.status === "cancelled") && (
          <div className="flex items-center gap-2 pt-1">
            <Button
              onClick={() => deleteMutation.mutate()}
              disabled={deleteMutation.isPending}
              variant="destructive"
              size="sm"
              data-testid={`button-delete-${job.id}`}
            >
              <Trash2 className="w-3.5 h-3.5 mr-1" />
              Delete
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
