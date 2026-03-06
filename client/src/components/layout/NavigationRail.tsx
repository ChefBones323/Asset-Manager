import { useLocation } from "wouter";
import {
  LayoutDashboard, Shield, Rss, Users, Activity, Settings,
  Clock, Brain,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { path: "/dashboard", label: "Mission Control", icon: LayoutDashboard },
  { path: "/governance", label: "Governance", icon: Shield },
  { path: "/feed", label: "Civic Feed", icon: Rss },
  { path: "/trust", label: "Trust Graph", icon: Users },
  { path: "/events", label: "Event Explorer", icon: Activity },
  { path: "/timeline", label: "Time Machine", icon: Clock },
  { path: "/ai-operator", label: "AI Operator", icon: Brain },
  { path: "/settings", label: "Settings", icon: Settings },
] as const;

export function NavigationRail() {
  const [location, navigate] = useLocation();

  return (
    <nav
      className="group/rail flex flex-col items-center py-3 gap-1 w-14 hover:w-48 transition-[width] duration-200 ease-out glass-panel border-r border-white/[0.06] shrink-0 overflow-hidden z-20"
      data-testid="navigation-rail"
    >
      <div className="flex items-center gap-2 px-3 mb-4 w-full min-w-0">
        <div className="w-8 h-8 rounded-lg bg-signal-blue/20 flex items-center justify-center shrink-0">
          <LayoutDashboard className="w-4 h-4 text-signal-blue" />
        </div>
        <span className="font-mono text-xs font-bold tracking-tight text-foreground whitespace-nowrap opacity-0 group-hover/rail:opacity-100 transition-opacity duration-200">
          CIVIC CP
        </span>
      </div>

      <div className="flex flex-col gap-0.5 w-full flex-1">
        {NAV_ITEMS.map(({ path, label, icon: Icon }) => {
          const active = location === path || (path === "/dashboard" && location === "/");
          return (
            <button
              key={path}
              onClick={() => navigate(path)}
              className={cn(
                "relative flex items-center gap-3 px-3 py-2.5 mx-1.5 rounded-lg text-xs transition-colors whitespace-nowrap min-w-0",
                active
                  ? "bg-white/[0.08] text-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-white/[0.04]"
              )}
              data-testid={`nav-${label.toLowerCase().replace(/\s/g, "-")}`}
            >
              {active && (
                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-r-full bg-signal-blue" />
              )}
              <Icon className={cn("w-5 h-5 shrink-0", active && "text-signal-blue")} />
              <span className="opacity-0 group-hover/rail:opacity-100 transition-opacity duration-200 font-medium">
                {label}
              </span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}
