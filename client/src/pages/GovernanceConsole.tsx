import { useQuery } from "@tanstack/react-query";
import { Link } from "wouter";
import { socialApi, type GovernanceProposal, type FeedPolicy } from "@/services/api";
import { GlassCard, GlassCardHeader, GlassCardTitle, GlassCardBody } from "@/components/common/Card";
import { Metric, MetricRow } from "@/components/common/Metric";
import { cn } from "@/lib/utils";
import { Shield, ArrowLeft, CheckCircle, XCircle, Clock, Vote, FileText } from "lucide-react";
import { useUIState } from "@/store/uiState";
import { Command } from "lucide-react";

function statusBadge(status: string) {
  const map: Record<string, { color: string; icon: typeof Clock }> = {
    open: { color: "text-signal-amber", icon: Clock },
    pending: { color: "text-signal-amber", icon: Clock },
    approved: { color: "text-signal-green", icon: CheckCircle },
    executed: { color: "text-signal-blue", icon: CheckCircle },
    rejected: { color: "text-signal-red", icon: XCircle },
  };
  const s = map[status] || map.pending!;
  const Icon = s.icon;
  return (
    <span className={cn("flex items-center gap-1 text-[10px] font-mono", s.color)}>
      <Icon className="w-3 h-3" />{status.toUpperCase()}
    </span>
  );
}

export default function GovernanceConsole() {
  const { openPalette } = useUIState();

  const { data: proposals, isLoading: loadingProposals } = useQuery<GovernanceProposal[]>({
    queryKey: ["/api/governance/proposals"],
    refetchInterval: 10000,
    retry: false,
    queryFn: () => socialApi.getGovernanceProposals(),
  });

  const { data: policiesData } = useQuery({
    queryKey: ["/admin/feed_policies"],
    refetchInterval: 10000,
    retry: false,
    queryFn: () => socialApi.getFeedPolicies(),
  });

  const policies = policiesData?.policies ?? [];
  const activeCount = policiesData?.active_count ?? 0;
  const allProposals = proposals ?? [];
  const openProposals = allProposals.filter((p) => p.status === "open" || p.status === "pending");
  const executedProposals = allProposals.filter((p) => p.status === "executed");

  return (
    <div className="min-h-screen bg-background flex flex-col" data-testid="governance-console">
      <header className="glass-panel border-b border-white/[0.06] px-4 py-2 flex items-center gap-3 shrink-0">
        <Link href="/" className="p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-white/[0.04] transition-colors" data-testid="nav-back">
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <Shield className="w-4 h-4 text-signal-purple" />
        <span className="font-mono text-sm font-bold tracking-tight text-foreground">GOVERNANCE CONSOLE</span>
        <button onClick={openPalette} className="ml-auto flex items-center gap-1 px-2 py-1 rounded-md text-xs text-muted-foreground hover:text-foreground hover:bg-white/[0.04]" data-testid="btn-palette">
          <Command className="w-3 h-3" />K
        </button>
      </header>

      <main className="flex-1 p-4 overflow-y-auto">
        <MetricRow className="mb-6">
          <Metric label="Total Proposals" value={allProposals.length} signal="purple" data-testid="metric-total-proposals" />
          <Metric label="Open" value={openProposals.length} signal="amber" data-testid="metric-open-proposals" />
          <Metric label="Executed" value={executedProposals.length} signal="green" data-testid="metric-executed-proposals" />
          <Metric label="Active Policies" value={activeCount} signal="blue" data-testid="metric-active-policies" />
        </MetricRow>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <GlassCard variant="elevated">
            <GlassCardHeader>
              <GlassCardTitle><Vote className="w-3 h-3 inline mr-1" />Proposal Queue</GlassCardTitle>
            </GlassCardHeader>
            <GlassCardBody className="space-y-2 max-h-[400px] overflow-y-auto">
              {loadingProposals ? (
                <div className="text-xs text-muted-foreground text-center py-4">Loading proposals...</div>
              ) : allProposals.length === 0 ? (
                <div className="text-xs text-muted-foreground text-center py-4" data-testid="proposals-empty">No proposals found</div>
              ) : (
                allProposals.map((p) => (
                  <div key={p.proposal_id} className="glass-inset rounded-md px-3 py-2 space-y-1" data-testid={`proposal-${p.proposal_id}`}>
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium text-foreground">{p.title || `Proposal ${p.proposal_id.slice(0, 8)}`}</span>
                      {statusBadge(p.status)}
                    </div>
                    <p className="text-[10px] text-muted-foreground line-clamp-2">{p.description}</p>
                    <div className="flex items-center gap-3 text-[10px] font-mono text-muted-foreground">
                      <span>Type: {p.proposal_type}</span>
                      <span>Domain: {p.domain}</span>
                      {p.total_votes !== undefined && <span>Votes: {p.total_votes}</span>}
                    </div>
                  </div>
                ))
              )}
            </GlassCardBody>
          </GlassCard>

          <GlassCard variant="elevated">
            <GlassCardHeader>
              <GlassCardTitle><FileText className="w-3 h-3 inline mr-1" />Policy Registry</GlassCardTitle>
            </GlassCardHeader>
            <GlassCardBody className="space-y-2 max-h-[400px] overflow-y-auto">
              {policies.length === 0 ? (
                <div className="text-xs text-muted-foreground text-center py-4" data-testid="policies-empty">No policies registered</div>
              ) : (
                policies.map((p: FeedPolicy) => (
                  <div key={p.policy_id} className="glass-inset rounded-md px-3 py-2 space-y-1" data-testid={`policy-row-${p.policy_id}`}>
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono font-medium text-foreground">{p.policy_id}</span>
                      <span className={cn("text-[10px] font-mono", p.approved ? "text-signal-green" : "text-signal-amber")}>
                        {p.approved ? "ACTIVE" : "PENDING"}
                      </span>
                    </div>
                    <div className="flex h-3 rounded-sm overflow-hidden">
                      <div className="bg-signal-blue" style={{ width: `${(p.timestamp_weight ?? 0) * 100}%` }} />
                      <div className="bg-signal-green" style={{ width: `${(p.reaction_weight ?? 0) * 100}%` }} />
                      <div className="bg-signal-amber" style={{ width: `${(p.trust_weight ?? 0) * 100}%` }} />
                      <div className="bg-signal-purple" style={{ width: `${(p.policy_weight ?? 0) * 100}%` }} />
                    </div>
                    <div className="flex gap-2 text-[9px] font-mono text-muted-foreground">
                      <span>ver: {(p.version || "").slice(0, 8)}</span>
                    </div>
                  </div>
                ))
              )}
            </GlassCardBody>
          </GlassCard>
        </div>
      </main>
    </div>
  );
}
