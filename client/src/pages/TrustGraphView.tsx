import { useState, useCallback } from "react";
import { TrustGraph, type TrustNode, type TrustEdge } from "@/components/trust/TrustGraph";
import { GlassCard, GlassCardBody } from "@/components/common/Card";
import { ExportMenu } from "@/components/common/ExportMenu";
import { Metric, MetricRow } from "@/components/common/Metric";
import { GlassModal } from "@/components/common/Modal";
import { cn } from "@/lib/utils";
import { Filter } from "lucide-react";
import { printTrustGraph } from "@/services/export/printService";

const DEMO_NODES: TrustNode[] = [
  { id: "user-1", label: "CivicMod", trust_score: 85, group: "moderator" },
  { id: "user-2", label: "Reporter1", trust_score: 72, group: "reporter" },
  { id: "user-3", label: "AnalystA", trust_score: 58, group: "analyst" },
  { id: "user-4", label: "DevOps", trust_score: 45, group: "infrastructure" },
  { id: "user-5", label: "NewUser", trust_score: 12, group: "citizen" },
  { id: "user-6", label: "TrustAdm", trust_score: 92, group: "admin" },
  { id: "user-7", label: "Editor", trust_score: 67, group: "moderator" },
  { id: "user-8", label: "Flagged", trust_score: -15, group: "citizen" },
];

const DEMO_EDGES: TrustEdge[] = [
  { source: "user-1", target: "user-2", weight: 0.8 },
  { source: "user-1", target: "user-3", weight: 0.6 },
  { source: "user-2", target: "user-4", weight: 0.5 },
  { source: "user-3", target: "user-5", weight: 0.3 },
  { source: "user-6", target: "user-1", weight: 0.9 },
  { source: "user-6", target: "user-7", weight: 0.7 },
  { source: "user-7", target: "user-2", weight: 0.4 },
  { source: "user-5", target: "user-8", weight: 0.2 },
  { source: "user-4", target: "user-6", weight: 0.6 },
];

export default function TrustGraphView() {
  const [selectedNode, setSelectedNode] = useState<TrustNode | null>(null);
  const [minTrust, setMinTrust] = useState(-100);

  const handleNodeClick = useCallback((node: TrustNode) => setSelectedNode(node), []);
  const handleClose = useCallback(() => setSelectedNode(null), []);

  const filteredNodes = DEMO_NODES.filter((n) => n.trust_score >= minTrust);
  const filteredNodeIds = new Set(filteredNodes.map((n) => n.id));
  const filteredEdges = DEMO_EDGES.filter((e) => filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target));

  return (
    <div className="h-full flex flex-col lg:flex-row gap-0 overflow-hidden" data-testid="trust-graph-view">
      <div className="lg:w-56 glass-panel border-r border-white/[0.06] p-3 space-y-3 shrink-0 overflow-y-auto">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <Filter className="w-3.5 h-3.5 text-muted-foreground" />
            <span className="mono-label">Filters</span>
          </div>
          <ExportMenu onExport={(f) => printTrustGraph(f)} label="Export" data-testid="export-trust" />
        </div>
        <div className="space-y-1.5">
          <label className="mono-label text-[10px]">Min Trust Score: {minTrust}</label>
          <input
            type="range"
            min={-100}
            max={100}
            value={minTrust}
            onChange={(e) => setMinTrust(Number(e.target.value))}
            className="w-full accent-primary"
            data-testid="filter-min-trust"
          />
        </div>
        <MetricRow className="flex-col">
          <Metric label="Nodes" value={filteredNodes.length} signal="green" data-testid="metric-nodes" />
          <Metric label="Edges" value={filteredEdges.length} signal="blue" data-testid="metric-edges" />
        </MetricRow>

        <div className="space-y-1">
          <span className="mono-label text-[10px]">Legend</span>
          <div className="space-y-1 text-[10px]">
            <div className="flex items-center gap-2"><div className="w-2.5 h-2.5 rounded-full bg-[#22c55e]" /><span className="text-muted-foreground">High Trust (&ge;70)</span></div>
            <div className="flex items-center gap-2"><div className="w-2.5 h-2.5 rounded-full bg-[#3b82f6]" /><span className="text-muted-foreground">Medium (30-70)</span></div>
            <div className="flex items-center gap-2"><div className="w-2.5 h-2.5 rounded-full bg-[#eab308]" /><span className="text-muted-foreground">Low (0-30)</span></div>
            <div className="flex items-center gap-2"><div className="w-2.5 h-2.5 rounded-full bg-[#ef4444]" /><span className="text-muted-foreground">Negative (&lt;0)</span></div>
          </div>
        </div>
      </div>

      <div className="flex-1 min-h-0 p-2">
        <GlassCard className="h-full" variant="elevated">
          <GlassCardBody className="h-full p-0">
            <TrustGraph
              nodes={filteredNodes}
              edges={filteredEdges}
              onNodeClick={handleNodeClick}
            />
          </GlassCardBody>
        </GlassCard>
      </div>

      <GlassModal open={!!selectedNode} onClose={handleClose} title="Trust Profile" size="sm" data-testid="trust-node-modal">
        {selectedNode && (
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-white/[0.06] flex items-center justify-center text-sm font-mono">
                {selectedNode.label.slice(0, 2).toUpperCase()}
              </div>
              <div>
                <div className="text-sm font-medium text-foreground">{selectedNode.label}</div>
                <div className="text-[10px] font-mono text-muted-foreground">{selectedNode.id}</div>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div className="glass-inset rounded-md px-3 py-2">
                <span className="mono-label text-[10px]">Trust Score</span>
                <p className={cn("font-mono text-xl font-bold", selectedNode.trust_score >= 50 ? "text-signal-green" : selectedNode.trust_score >= 0 ? "text-signal-amber" : "text-signal-red")} data-testid="node-trust-score">
                  {selectedNode.trust_score}
                </p>
              </div>
              <div className="glass-inset rounded-md px-3 py-2">
                <span className="mono-label text-[10px]">Group</span>
                <p className="font-mono text-sm text-foreground mt-0.5">{selectedNode.group || "N/A"}</p>
              </div>
            </div>
          </div>
        )}
      </GlassModal>
    </div>
  );
}
