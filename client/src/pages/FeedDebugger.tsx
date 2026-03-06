import { useState } from "react";
import { GlassCard, GlassCardHeader, GlassCardTitle, GlassCardBody } from "@/components/common/Card";
import { ExportMenu } from "@/components/common/ExportMenu";
import { RankingBreakdownChart, type RankingBreakdown } from "@/components/debugger/RankingBreakdownChart";
import { Metric, MetricRow } from "@/components/common/Metric";
import { cn } from "@/lib/utils";
import { Search } from "lucide-react";
import { printFeedSnapshot } from "@/services/export/printService";

const SAMPLE_POSTS = [
  { id: "post-1", label: "Governance Update", recency: 0.35, reactions: 0.28, trust: 0.22, policy: 0.15, total: 4.82, rank: 1 },
  { id: "post-2", label: "Infrastructure Report", recency: 0.20, reactions: 0.15, trust: 0.40, policy: 0.25, total: 3.91, rank: 2 },
  { id: "post-3", label: "Trust Analysis", recency: 0.10, reactions: 0.32, trust: 0.35, policy: 0.23, total: 2.67, rank: 3 },
  { id: "post-4", label: "Community Discussion", recency: 0.42, reactions: 0.08, trust: 0.10, policy: 0.40, total: 1.44, rank: 4 },
];

export default function FeedDebugger() {
  const [selected, setSelected] = useState(SAMPLE_POSTS[0]);

  const breakdown: RankingBreakdown = {
    recency: selected.recency,
    reactions: selected.reactions,
    trust: selected.trust,
    policy: selected.policy,
  };

  return (
    <div className="h-full p-4 overflow-y-auto" data-testid="feed-debugger">
      <div className="flex items-center justify-end mb-3">
        <ExportMenu onExport={(f) => printFeedSnapshot(f)} label="Export Snapshot" data-testid="export-feed" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-4 max-w-5xl">
        <GlassCard>
          <GlassCardHeader>
            <GlassCardTitle><Search className="w-3 h-3 inline mr-1" />Select Post</GlassCardTitle>
          </GlassCardHeader>
          <GlassCardBody className="space-y-1.5">
            {SAMPLE_POSTS.map((post) => (
              <button
                key={post.id}
                onClick={() => setSelected(post)}
                className={cn(
                  "w-full text-left px-3 py-2 rounded-md text-xs transition-colors",
                  selected.id === post.id
                    ? "bg-white/[0.08] text-foreground"
                    : "hover:bg-white/[0.04] text-muted-foreground"
                )}
                data-testid={`select-post-${post.id}`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium">{post.label}</span>
                  <span className="font-mono text-[10px]">#{post.rank}</span>
                </div>
                <span className="font-mono text-[10px]">Score: {post.total.toFixed(2)}</span>
              </button>
            ))}
          </GlassCardBody>
        </GlassCard>

        <div className="space-y-4">
          <MetricRow>
            <Metric label="Rank Position" value={`#${selected.rank}`} signal="blue" data-testid="metric-rank" />
            <Metric label="Final Score" value={selected.total.toFixed(3)} signal="green" data-testid="metric-score" />
            <Metric label="Recency" value={(selected.recency * 100).toFixed(0)} unit="%" data-testid="metric-recency" />
            <Metric label="Trust Factor" value={(selected.trust * 100).toFixed(0)} unit="%" data-testid="metric-trust-factor" />
          </MetricRow>

          <GlassCard variant="elevated">
            <GlassCardHeader>
              <GlassCardTitle>Ranking Breakdown</GlassCardTitle>
            </GlassCardHeader>
            <GlassCardBody>
              <RankingBreakdownChart
                breakdown={breakdown}
                total={selected.recency + selected.reactions + selected.trust + selected.policy}
              />
            </GlassCardBody>
          </GlassCard>

          <GlassCard>
            <GlassCardHeader>
              <GlassCardTitle>Score Components</GlassCardTitle>
            </GlassCardHeader>
            <GlassCardBody>
              <pre className="text-[11px] font-mono text-foreground glass-inset rounded-md p-3 overflow-auto" data-testid="score-raw-data">
{JSON.stringify({
  content_id: selected.id,
  rank: selected.rank,
  final_score: selected.total,
  components: {
    recency_contribution: selected.recency,
    reaction_contribution: selected.reactions,
    trust_contribution: selected.trust,
    policy_modifier: selected.policy,
  },
  weights_used: {
    timestamp_weight: 0.40,
    reaction_weight: 0.25,
    trust_weight: 0.20,
    policy_weight: 0.15,
  },
}, null, 2)}
              </pre>
            </GlassCardBody>
          </GlassCard>
        </div>
      </div>
    </div>
  );
}
