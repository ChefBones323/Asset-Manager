import { memo } from "react";
import { cn } from "@/lib/utils";

export interface RankingBreakdown {
  recency: number;
  reactions: number;
  trust: number;
  policy: number;
}

interface RankingBreakdownChartProps {
  breakdown: RankingBreakdown;
  total: number;
  className?: string;
}

const segments = [
  { key: "recency" as const, label: "Recency", color: "bg-signal-blue" },
  { key: "reactions" as const, label: "Reactions", color: "bg-signal-green" },
  { key: "trust" as const, label: "Trust", color: "bg-signal-amber" },
  { key: "policy" as const, label: "Policy", color: "bg-signal-purple" },
];

export const RankingBreakdownChart = memo(function RankingBreakdownChart({
  breakdown,
  total,
  className,
}: RankingBreakdownChartProps) {
  const safeTotal = total > 0 ? total : 1;

  return (
    <div className={cn("space-y-3", className)} data-testid="ranking-breakdown">
      <div className="flex h-6 rounded-md overflow-hidden glass-inset">
        {segments.map(({ key, color }) => {
          const pct = (breakdown[key] / safeTotal) * 100;
          if (pct <= 0) return null;
          return (
            <div
              key={key}
              className={cn(color, "flex items-center justify-center text-[9px] font-mono font-bold text-white transition-all duration-300")}
              style={{ width: `${Math.max(pct, 2)}%` }}
              data-testid={`breakdown-bar-${key}`}
            >
              {pct >= 8 ? `${pct.toFixed(0)}%` : ""}
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-2 gap-2">
        {segments.map(({ key, label, color }) => (
          <div key={key} className="flex items-center gap-2 text-xs">
            <div className={cn("w-2.5 h-2.5 rounded-sm", color)} />
            <span className="text-muted-foreground">{label}</span>
            <span className="ml-auto font-mono text-foreground" data-testid={`breakdown-value-${key}`}>
              {breakdown[key].toFixed(3)}
            </span>
            <span className="font-mono text-muted-foreground text-[10px]">
              ({((breakdown[key] / safeTotal) * 100).toFixed(1)}%)
            </span>
          </div>
        ))}
      </div>
    </div>
  );
});
