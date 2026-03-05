import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { useLocation } from "wouter";
import { useUIState } from "@/store/uiState";
import {
  Search, Terminal, Shield, Rss, Users, Server, Activity, Stethoscope,
  ArrowRight, Command,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface CommandEntry {
  id: string;
  label: string;
  category: "governance" | "feed" | "trust" | "infrastructure" | "events" | "diagnostics";
  keywords: string[];
  action: () => void;
  icon: typeof Terminal;
}

const categoryIcons: Record<string, typeof Terminal> = {
  governance: Shield,
  feed: Rss,
  trust: Users,
  infrastructure: Server,
  events: Activity,
  diagnostics: Stethoscope,
};

const categoryColors: Record<string, string> = {
  governance: "text-signal-purple",
  feed: "text-signal-blue",
  trust: "text-signal-green",
  infrastructure: "text-signal-amber",
  events: "text-chart-1",
  diagnostics: "text-signal-red",
};

export function CommandPalette() {
  const { paletteOpen, closePalette } = useUIState();
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const [, navigate] = useLocation();

  const commands: CommandEntry[] = useMemo(() => [
    { id: "nav_mission", label: "Open Mission Control", category: "diagnostics", keywords: ["mission", "dashboard", "home"], action: () => navigate("/"), icon: Terminal },
    { id: "nav_governance", label: "Open Governance Console", category: "governance", keywords: ["governance", "proposals", "voting"], action: () => navigate("/governance"), icon: Shield },
    { id: "nav_feed_debugger", label: "Open Feed Debugger", category: "feed", keywords: ["feed", "debugger", "ranking", "explain"], action: () => navigate("/feed-debugger"), icon: Rss },
    { id: "nav_trust", label: "Open Trust Graph", category: "trust", keywords: ["trust", "graph", "reputation", "network"], action: () => navigate("/trust-graph"), icon: Users },
    { id: "nav_events", label: "Open Event Explorer", category: "events", keywords: ["events", "explorer", "inspect", "stream"], action: () => navigate("/events"), icon: Activity },
    { id: "simulate_feed", label: "Simulate Feed Policy", category: "feed", keywords: ["simulate", "feed", "policy", "ranking"], action: () => navigate("/feed-debugger"), icon: Rss },
    { id: "create_proposal", label: "Create Governance Proposal", category: "governance", keywords: ["create", "proposal", "governance", "vote"], action: () => navigate("/governance"), icon: Shield },
    { id: "show_workers", label: "Show Active Workers", category: "infrastructure", keywords: ["workers", "active", "lease", "heartbeat"], action: () => navigate("/"), icon: Server },
    { id: "inspect_events", label: "Inspect Event Stream", category: "events", keywords: ["inspect", "events", "stream", "filter"], action: () => navigate("/events"), icon: Activity },
    { id: "explain_ranking", label: "Explain Feed Ranking", category: "feed", keywords: ["explain", "ranking", "score", "breakdown"], action: () => navigate("/feed-debugger"), icon: Rss },
    { id: "replay_projections", label: "Replay Projections", category: "infrastructure", keywords: ["replay", "projections", "rebuild", "state"], action: () => navigate("/"), icon: Server },
    { id: "system_health", label: "System Health Check", category: "diagnostics", keywords: ["system", "health", "status", "check"], action: () => navigate("/"), icon: Stethoscope },
    { id: "inspect_trust", label: "Inspect User Trust", category: "trust", keywords: ["inspect", "trust", "user", "score", "profile"], action: () => navigate("/trust-graph"), icon: Users },
    { id: "show_dlq", label: "View Dead Letter Queue", category: "infrastructure", keywords: ["dead", "letter", "queue", "dlq", "failed"], action: () => navigate("/"), icon: Server },
    { id: "filter_by_domain", label: "Filter Events by Domain", category: "events", keywords: ["filter", "domain", "events", "content", "trust"], action: () => navigate("/events"), icon: Activity },
    { id: "compare_policies", label: "Compare Feed Policies", category: "feed", keywords: ["compare", "policies", "feed", "weights"], action: () => navigate("/feed-debugger"), icon: Rss },
  ], [navigate]);

  const filtered = useMemo(() => {
    if (!query.trim()) return commands;
    const lower = query.toLowerCase();
    const terms = lower.split(/\s+/);
    return commands.filter((cmd) => {
      const searchable = `${cmd.label} ${cmd.category} ${cmd.keywords.join(" ")}`.toLowerCase();
      return terms.every((t) => searchable.includes(t));
    });
  }, [query, commands]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [filtered.length]);

  useEffect(() => {
    if (paletteOpen) {
      setQuery("");
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [paletteOpen]);

  const executeCommand = useCallback((cmd: CommandEntry) => {
    cmd.action();
    closePalette();
  }, [closePalette]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((i) => Math.min(i + 1, filtered.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((i) => Math.max(i - 1, 0));
      } else if (e.key === "Enter" && filtered[selectedIndex]) {
        e.preventDefault();
        executeCommand(filtered[selectedIndex]);
      } else if (e.key === "Escape") {
        closePalette();
      }
    },
    [filtered, selectedIndex, executeCommand, closePalette]
  );

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        useUIState.getState().togglePalette();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  useEffect(() => {
    if (listRef.current) {
      const selected = listRef.current.children[selectedIndex] as HTMLElement;
      selected?.scrollIntoView({ block: "nearest" });
    }
  }, [selectedIndex]);

  if (!paletteOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh]" data-testid="command-palette">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={closePalette} />
      <div className="glass-panel-elevated rounded-xl w-full max-w-xl relative z-10 animate-in fade-in-0 zoom-in-95 duration-150">
        <div className="flex items-center gap-3 px-4 py-3 border-b border-white/[0.06]">
          <Search className="w-4 h-4 text-muted-foreground shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a command..."
            className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground outline-none font-mono"
            data-testid="palette-input"
          />
          <kbd className="mono-label px-1.5 py-0.5 rounded border border-white/[0.1] text-[10px]">ESC</kbd>
        </div>
        <div ref={listRef} className="max-h-[320px] overflow-y-auto py-1" data-testid="palette-results">
          {filtered.length === 0 && (
            <div className="px-4 py-8 text-center text-sm text-muted-foreground">No matching commands</div>
          )}
          {filtered.map((cmd, i) => {
            const CatIcon = categoryIcons[cmd.category] || Terminal;
            return (
              <button
                key={cmd.id}
                onClick={() => executeCommand(cmd)}
                className={cn(
                  "w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors",
                  i === selectedIndex ? "bg-white/[0.06]" : "hover:bg-white/[0.03]"
                )}
                data-testid={`palette-cmd-${cmd.id}`}
              >
                <CatIcon className={cn("w-4 h-4 shrink-0", categoryColors[cmd.category])} />
                <div className="flex-1 min-w-0">
                  <span className="text-sm text-foreground">{cmd.label}</span>
                </div>
                <span className={cn("mono-label text-[10px]", categoryColors[cmd.category])}>
                  {cmd.category}
                </span>
                {i === selectedIndex && <ArrowRight className="w-3 h-3 text-muted-foreground" />}
              </button>
            );
          })}
        </div>
        <div className="px-4 py-2 border-t border-white/[0.06] flex items-center gap-4">
          <span className="mono-label text-[10px] flex items-center gap-1">
            <Command className="w-3 h-3" />K to toggle
          </span>
          <span className="mono-label text-[10px]">&uarr;&darr; navigate</span>
          <span className="mono-label text-[10px]">&crarr; execute</span>
        </div>
      </div>
    </div>
  );
}
