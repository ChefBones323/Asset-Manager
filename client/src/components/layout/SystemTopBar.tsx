import { useQuery } from "@tanstack/react-query";
import { socialApi, type EventMetrics } from "@/services/api";
import { isConnected } from "@/services/websocket";
import { useUIState } from "@/store/uiState";
import { useAuth } from "@/hooks/use-auth";
import {
  Wifi, WifiOff, LogOut, Command, PenSquare,
} from "lucide-react";

export function SystemTopBar() {
  const { openPalette, openComposer } = useUIState();
  const { logout } = useAuth();
  const connected = isConnected();

  const { data: metrics } = useQuery<EventMetrics>({
    queryKey: ["/admin/event_metrics"],
    refetchInterval: 5000,
    retry: false,
    queryFn: async () => socialApi.getEventMetrics(),
  });

  return (
    <header
      className="glass-panel border-b border-white/[0.06] px-4 py-2 flex items-center gap-4 shrink-0 z-10"
      data-testid="system-top-bar"
    >
      <div className="flex items-center gap-2">
        <div className="w-2 h-2 rounded-full bg-signal-blue animate-pulse-glow" />
        <span className="font-mono text-sm font-bold tracking-tight text-foreground">
          CIVIC MISSION CONTROL
        </span>
      </div>

      <div className="ml-auto flex items-center gap-3">
        <button
          onClick={openComposer}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-signal-blue/20 text-signal-blue hover:bg-signal-blue/30 transition-colors"
          data-testid="btn-compose"
        >
          <PenSquare className="w-3.5 h-3.5" />
          <span>Compose</span>
        </button>

        <div className="h-4 w-px bg-white/[0.08]" />

        <div className="flex items-center gap-1.5 text-[10px] font-mono text-muted-foreground">
          {connected ? (
            <Wifi className="w-3 h-3 text-signal-green" />
          ) : (
            <WifiOff className="w-3 h-3 text-signal-red" />
          )}
          <span data-testid="status-connection">{connected ? "LIVE" : "OFFLINE"}</span>
        </div>

        <span
          className="font-mono text-[10px] text-muted-foreground"
          data-testid="status-event-rate"
        >
          {(metrics?.events_per_second ?? 0).toFixed(1)}/s
        </span>

        <button
          onClick={openPalette}
          className="flex items-center gap-1 px-2 py-1 rounded-md text-xs text-muted-foreground hover:text-foreground hover:bg-white/[0.04] transition-colors"
          data-testid="btn-open-palette"
        >
          <Command className="w-3 h-3" />
          <span className="hidden md:inline">K</span>
        </button>

        <button
          onClick={() => logout()}
          className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-white/[0.04] transition-colors"
          data-testid="btn-logout"
        >
          <LogOut className="w-3.5 h-3.5" />
        </button>
      </div>
    </header>
  );
}
