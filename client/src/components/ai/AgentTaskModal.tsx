import { useState, useCallback, useEffect, useRef } from "react";
import { useUIState } from "@/store/uiState";
import { runAgentTask, type AgentRunResult, type AgentToolCall, type AgentToolResult } from "@/services/agentApi";
import { cn } from "@/lib/utils";
import {
  Brain, X, Play, CheckCircle2, AlertTriangle, Clock,
  ChevronDown, ChevronRight, Shield, FileText, Search,
  Globe, Zap, Loader2,
} from "lucide-react";

const toolIcons: Record<string, typeof Brain> = {
  filesystem_read: FileText,
  filesystem_write: FileText,
  web_search: Search,
  browser_open: Globe,
  skill_run: Zap,
};

const approvalColors: Record<string, string> = {
  auto: "text-signal-green",
  confirmation: "text-signal-amber",
  destructive: "text-signal-red",
};

function StepCard({ call, result, index }: { call: AgentToolCall; result?: AgentToolResult; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const ToolIcon = toolIcons[call.tool] || Brain;
  const approvalLevel = result?.approval_level || result?.approval || "auto";
  const approvalColor = approvalColors[approvalLevel] || "text-muted-foreground";
  const isError = result?.status === "error";
  const isProposal = result?.status === "proposal_created";

  return (
    <div className="glass-inset rounded-lg p-3 space-y-2" data-testid={`agent-step-${index}`}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 text-left"
        data-testid={`agent-step-toggle-${index}`}
      >
        <span className="mono-label text-[10px] text-muted-foreground w-6">#{index + 1}</span>
        <ToolIcon className={cn("w-3.5 h-3.5 shrink-0", approvalColor)} />
        <span className="text-xs text-foreground flex-1 truncate">{call.description || call.tool}</span>
        {isError && <AlertTriangle className="w-3 h-3 text-signal-red shrink-0" />}
        {isProposal && <Shield className="w-3 h-3 text-signal-amber shrink-0" />}
        {!isError && !isProposal && result && <CheckCircle2 className="w-3 h-3 text-signal-green shrink-0" />}
        {expanded ? <ChevronDown className="w-3 h-3 text-muted-foreground" /> : <ChevronRight className="w-3 h-3 text-muted-foreground" />}
      </button>

      {expanded && (
        <div className="ml-6 space-y-1.5 text-[11px] font-mono">
          <div>
            <span className="text-muted-foreground">Tool: </span>
            <span className="text-foreground">{call.tool}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Args: </span>
            <span className="text-foreground">{JSON.stringify(call.args)}</span>
          </div>
          {result && (
            <div>
              <span className="text-muted-foreground">Status: </span>
              <span className={cn(isError ? "text-signal-red" : isProposal ? "text-signal-amber" : "text-signal-green")}>
                {result.status}
              </span>
            </div>
          )}
          {result?.message && (
            <div className="text-muted-foreground text-[10px] leading-relaxed mt-1">{result.message}</div>
          )}
          {result?.proposal_id && (
            <div>
              <span className="text-muted-foreground">Proposal: </span>
              <span className="text-signal-amber">{result.proposal_id}</span>
            </div>
          )}
          {result?.error && (
            <div className="text-signal-red text-[10px] mt-1">{result.error}</div>
          )}
        </div>
      )}
    </div>
  );
}

export function AgentTaskModal() {
  const { agentModalOpen, agentModalTask, closeAgentModal } = useUIState();
  const [task, setTask] = useState("");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<AgentRunResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (agentModalOpen) {
      setTask(agentModalTask || "");
      setResult(null);
      setError(null);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [agentModalOpen, agentModalTask]);

  const handleRun = useCallback(async () => {
    if (!task.trim() || running) return;
    setRunning(true);
    setResult(null);
    setError(null);
    try {
      const res = await runAgentTask(task.trim());
      setResult(res);
    } catch (err: any) {
      setError(err.message || "Failed to run agent task");
    } finally {
      setRunning(false);
    }
  }, [task, running]);

  if (!agentModalOpen) return null;

  const hasProposals = result?.results?.some(r => r.status === "proposal_created") || false;
  const hasErrors = result?.status === "error";

  return (
    <div className="fixed inset-0 z-[110] flex items-center justify-center p-4" data-testid="agent-task-modal">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={closeAgentModal} />
      <div className="glass-panel-elevated rounded-xl w-full max-w-2xl relative z-10 animate-in fade-in-0 zoom-in-95 duration-150 max-h-[85vh] flex flex-col">
        <div className="flex items-center gap-3 px-5 py-4 border-b border-white/[0.06] shrink-0">
          <Brain className="w-5 h-5 text-signal-amber" />
          <div className="flex-1">
            <h2 className="text-sm font-semibold text-foreground">OpenClaw Operator</h2>
            <p className="text-[10px] text-muted-foreground">Plan → Tools → Execute → Govern</p>
          </div>
          <button onClick={closeAgentModal} className="p-1.5 rounded-md hover:bg-white/[0.04] transition-colors" data-testid="btn-close-agent-modal">
            <X className="w-4 h-4 text-muted-foreground" />
          </button>
        </div>

        <div className="px-5 py-4 border-b border-white/[0.06] shrink-0">
          <div className="flex items-center gap-2">
            <input
              ref={inputRef}
              value={task}
              onChange={(e) => setTask(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") handleRun(); }}
              placeholder="Describe a task for the operator..."
              className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground outline-none font-mono"
              disabled={running}
              data-testid="agent-task-input"
            />
            <button
              onClick={handleRun}
              disabled={!task.trim() || running}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors",
                task.trim() && !running
                  ? "bg-signal-amber/20 text-signal-amber hover:bg-signal-amber/30"
                  : "bg-white/[0.03] text-muted-foreground/30 cursor-not-allowed"
              )}
              data-testid="btn-run-agent-task"
            >
              {running ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
              {running ? "Running..." : "Execute"}
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4 min-h-0">
          {running && !result && (
            <div className="flex flex-col items-center justify-center py-12 space-y-3">
              <div className="w-10 h-10 border-2 border-signal-amber border-t-transparent rounded-full animate-spin" />
              <p className="text-xs text-muted-foreground">Planning and executing task...</p>
            </div>
          )}

          {error && (
            <div className="glass-inset rounded-lg p-4 border border-signal-red/20" data-testid="agent-error">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle className="w-4 h-4 text-signal-red" />
                <span className="text-sm font-medium text-signal-red">Execution Failed</span>
              </div>
              <p className="text-xs text-muted-foreground">{error}</p>
            </div>
          )}

          {result && (
            <>
              <div className="flex items-center gap-3" data-testid="agent-result-header">
                <div className={cn(
                  "w-8 h-8 rounded-lg flex items-center justify-center",
                  hasErrors ? "bg-signal-red/20" : hasProposals ? "bg-signal-amber/20" : "bg-signal-green/20"
                )}>
                  {hasErrors ? <AlertTriangle className="w-4 h-4 text-signal-red" /> :
                   hasProposals ? <Shield className="w-4 h-4 text-signal-amber" /> :
                   <CheckCircle2 className="w-4 h-4 text-signal-green" />}
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-foreground">
                    {hasErrors ? "Task Failed" : hasProposals ? "Awaiting Approval" : "Task Complete"}
                  </p>
                  <p className="text-[10px] text-muted-foreground">
                    {result.steps_executed} step{result.steps_executed !== 1 ? "s" : ""} executed
                  </p>
                </div>
              </div>

              {result.plan.length > 0 && (
                <div data-testid="agent-plan">
                  <span className="mono-label text-[10px] text-muted-foreground">Plan</span>
                  <div className="mt-1.5 space-y-1">
                    {result.plan.map((step, i) => (
                      <div key={i} className="flex items-center gap-2 text-xs">
                        <span className="mono-label text-[10px] text-muted-foreground w-5">{i + 1}.</span>
                        <Clock className="w-3 h-3 text-muted-foreground shrink-0" />
                        <span className="text-foreground">{step}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {result.tool_calls.length > 0 && (
                <div data-testid="agent-tool-calls">
                  <span className="mono-label text-[10px] text-muted-foreground">Tool Calls</span>
                  <div className="mt-1.5 space-y-1.5">
                    {result.tool_calls.map((call, i) => (
                      <StepCard key={i} call={call} result={result.results[i]} index={i} />
                    ))}
                  </div>
                </div>
              )}

              {result.error && (
                <div className="glass-inset rounded-lg p-3 border border-signal-red/20" data-testid="agent-task-error">
                  <span className="mono-label text-[10px] text-signal-red">Error</span>
                  <p className="text-xs text-muted-foreground mt-1">{result.error}</p>
                </div>
              )}
            </>
          )}

          {!running && !result && !error && (
            <div className="flex flex-col items-center justify-center py-12 space-y-3 text-center">
              <Brain className="w-12 h-12 text-signal-amber/30" />
              <div>
                <p className="text-sm text-foreground font-medium">OpenClaw Operator Runtime</p>
                <p className="text-[10px] text-muted-foreground mt-1 max-w-sm">
                  Describe a task and the operator will plan it, select tools, and execute.
                  Destructive actions require human approval through the governance pipeline.
                </p>
              </div>
            </div>
          )}
        </div>

        <div className="px-5 py-3 border-t border-white/[0.06] flex items-center gap-4 shrink-0">
          <span className="mono-label text-[10px] flex items-center gap-1">
            <Shield className="w-3 h-3 text-signal-green" /> read = auto
          </span>
          <span className="mono-label text-[10px] flex items-center gap-1">
            <Shield className="w-3 h-3 text-signal-amber" /> browse = confirm
          </span>
          <span className="mono-label text-[10px] flex items-center gap-1">
            <Shield className="w-3 h-3 text-signal-red" /> write = approval
          </span>
        </div>
      </div>
    </div>
  );
}
