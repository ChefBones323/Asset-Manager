import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

type MetricTrend = "up" | "down" | "neutral";
type MetricSignal = "blue" | "green" | "amber" | "red" | "purple" | "default";

interface MetricProps {
  label: string;
  value: string | number;
  unit?: string;
  trend?: MetricTrend;
  trendValue?: string;
  signal?: MetricSignal;
  className?: string;
  "data-testid"?: string;
}

const signalColors: Record<MetricSignal, string> = {
  blue: "text-signal-blue",
  green: "text-signal-green",
  amber: "text-signal-amber",
  red: "text-signal-red",
  purple: "text-signal-purple",
  default: "text-foreground",
};

const trendIcons: Record<MetricTrend, typeof TrendingUp> = {
  up: TrendingUp,
  down: TrendingDown,
  neutral: Minus,
};

const trendColors: Record<MetricTrend, string> = {
  up: "text-signal-green",
  down: "text-signal-red",
  neutral: "text-muted-foreground",
};

export function Metric({
  label,
  value,
  unit,
  trend,
  trendValue,
  signal = "default",
  className,
  ...props
}: MetricProps) {
  const TrendIcon = trend ? trendIcons[trend] : null;

  return (
    <div
      className={cn("glass-panel rounded-lg px-4 py-3 min-w-[120px]", className)}
      data-testid={props["data-testid"]}
    >
      <div className="mono-label mb-1.5" data-testid={`metric-label-${label.toLowerCase().replace(/\s/g, "-")}`}>
        {label}
      </div>
      <div className="flex items-baseline gap-1.5">
        <span
          className={cn(
            "font-mono text-2xl font-bold tracking-tight leading-none",
            signalColors[signal]
          )}
          data-testid={`metric-value-${label.toLowerCase().replace(/\s/g, "-")}`}
        >
          {value}
        </span>
        {unit && (
          <span className="font-mono text-xs text-muted-foreground">{unit}</span>
        )}
      </div>
      {trend && TrendIcon && (
        <div className={cn("flex items-center gap-1 mt-1.5", trendColors[trend])}>
          <TrendIcon className="w-3 h-3" />
          {trendValue && (
            <span className="font-mono text-[10px]">{trendValue}</span>
          )}
        </div>
      )}
    </div>
  );
}

interface MetricRowProps {
  children: React.ReactNode;
  className?: string;
}

export function MetricRow({ children, className }: MetricRowProps) {
  return (
    <div className={cn("flex gap-3 flex-wrap", className)}>
      {children}
    </div>
  );
}
