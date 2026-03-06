import { useState, useCallback, useRef, useEffect } from "react";
import { useLocation } from "wouter";
import {
  processQuery, SUGGESTED_QUERIES,
  analyzeFeedRanking, explainTrustScore, tracePolicyImpact,
  findInfluentialNodes, summarizeEvents, detectAnomalies,
  type AnalysisResult,
} from "@/services/ai/analysisService";
import { GlassCard, GlassCardHeader, GlassCardTitle, GlassCardBody } from "@/components/common/Card";
import { cn } from "@/lib/utils";
import {
  Brain, Send, Sparkles, BarChart3, Shield, Users, Activity,
  AlertTriangle, ChevronRight, ExternalLink,
} from "lucide-react";

const typeIcons: Record<string, typeof Brain> = {
  ranking: BarChart3,
  trust: Users,
  policy: Shield,
  influence: Activity,
  event_chain: Activity,
};

const typeColors: Record<string, string> = {
  ranking: "text-signal-blue",
  trust: "text-signal-green",
  policy: "text-signal-purple",
  influence: "text-signal-amber",
  event_chain: "text-chart-1",
};

interface ConversationEntry {
  id: string;
  query: string;
  result: AnalysisResult;
  timestamp: string;
}

export function CivicOperatorPanel() {
  const [query, setQuery] = useState("");
  const [conversation, setConversation] = useState<ConversationEntry[]>([]);
  const [processing, setProcessing] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [, navigate] = useLocation();

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [conversation]);

  const runAnalysis = useCallback((queryText: string, analysisFn?: () => AnalysisResult) => {
    setProcessing(true);
    setTimeout(() => {
      const result = analysisFn ? analysisFn() : processQuery(queryText);
      setConversation((prev) => [...prev, {
        id: `conv-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
        query: queryText,
        result,
        timestamp: new Date().toISOString(),
      }]);
      setProcessing(false);
      setQuery("");
    }, 300);
  }, []);

  const handleSubmit = useCallback(() => {
    if (!query.trim() || processing) return;
    runAnalysis(query.trim());
  }, [query, processing, runAnalysis]);

  const handleSuggestedQuery = useCallback((sq: typeof SUGGESTED_QUERIES[number]) => {
    const fnMap: Record<string, () => AnalysisResult> = {
      analyzeFeedRanking: () => analyzeFeedRanking(),
      findInfluentialNodes: () => findInfluentialNodes(),
      tracePolicyImpact: () => tracePolicyImpact(),
      summarizeEvents: () => summarizeEvents(),
      detectAnomalies: () => detectAnomalies(),
    };
    runAnalysis(sq.label, fnMap[sq.action]);
  }, [runAnalysis]);

  const handleEventLink = useCallback((eventId: string) => {
    navigate("/events");
  }, [navigate]);

  return (
    <div className="h-full flex flex-col" data-testid="civic-operator-panel">
      <div className="flex-1 flex flex-col lg:flex-row gap-0 min-h-0 overflow-hidden">
        <div className="lg:w-56 glass-panel border-r border-white/[0.06] p-3 space-y-3 shrink-0 overflow-y-auto">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-signal-amber" />
            <span className="mono-label">Suggested</span>
          </div>
          <div className="space-y-1.5">
            {SUGGESTED_QUERIES.map((sq) => (
              <button
                key={sq.id}
                onClick={() => handleSuggestedQuery(sq)}
                className="w-full text-left px-2.5 py-2 rounded-md text-xs hover:bg-white/[0.04] transition-colors group"
                data-testid={`suggested-query-${sq.id}`}
              >
                <div className="flex items-center gap-1.5">
                  <ChevronRight className="w-3 h-3 text-muted-foreground group-hover:text-foreground transition-colors" />
                  <span className="text-foreground font-medium">{sq.label}</span>
                </div>
                <p className="text-[10px] text-muted-foreground mt-0.5 ml-4.5">{sq.description}</p>
              </button>
            ))}
          </div>

          <div className="pt-2 border-t border-white/[0.06]">
            <span className="mono-label text-[10px]">Read-Only Mode</span>
            <p className="text-[10px] text-muted-foreground mt-1">
              AI Operator analyzes existing data. It never modifies system state.
            </p>
          </div>
        </div>

        <div className="flex-1 flex flex-col min-h-0">
          <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
            {conversation.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full text-center space-y-3">
                <Brain className="w-12 h-12 text-signal-amber/40" />
                <div>
                  <p className="text-sm text-foreground font-medium">Civic Intelligence Operator</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Ask questions about feed rankings, trust scores, policy impacts, or system behavior.
                  </p>
                </div>
              </div>
            )}

            {conversation.map((entry) => {
              const ResultIcon = typeIcons[entry.result.type] || Brain;
              const color = typeColors[entry.result.type] || "text-foreground";

              return (
                <div key={entry.id} className="space-y-2" data-testid={`conversation-${entry.id}`}>
                  <div className="flex items-start gap-2">
                    <div className="w-6 h-6 rounded-full bg-white/[0.06] flex items-center justify-center shrink-0 mt-0.5">
                      <span className="text-[10px] font-mono">OP</span>
                    </div>
                    <p className="text-sm text-foreground">{entry.query}</p>
                  </div>

                  <GlassCard variant="elevated" className="ml-8" data-testid={`insight-card-${entry.result.type}`}>
                    <GlassCardHeader>
                      <GlassCardTitle>
                        <ResultIcon className={cn("w-3.5 h-3.5 inline mr-1.5", color)} />
                        {entry.result.title}
                      </GlassCardTitle>
                      <div className="flex items-center gap-2">
                        <span className={cn("text-[10px] font-mono", entry.result.confidence >= 0.7 ? "text-signal-green" : entry.result.confidence >= 0.4 ? "text-signal-amber" : "text-signal-red")}>
                          {(entry.result.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                    </GlassCardHeader>
                    <GlassCardBody className="space-y-2">
                      <p className="text-xs text-muted-foreground">{entry.result.summary}</p>
                      <div className="space-y-1">
                        {entry.result.details.map((detail, i) => (
                          <p key={i} className="text-xs text-foreground font-mono leading-relaxed">
                            {detail}
                          </p>
                        ))}
                      </div>
                      {entry.result.referencedEvents.length > 0 && (
                        <div className="pt-2 border-t border-white/[0.06]">
                          <span className="mono-label text-[9px]">Referenced Events</span>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {entry.result.referencedEvents.map((eid) => (
                              <button
                                key={eid}
                                onClick={() => handleEventLink(eid)}
                                className="flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono text-signal-blue hover:bg-white/[0.04] transition-colors"
                                data-testid={`event-link-${eid.slice(0, 12)}`}
                              >
                                <ExternalLink className="w-2.5 h-2.5" />
                                {eid.slice(0, 16)}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}
                    </GlassCardBody>
                  </GlassCard>
                </div>
              );
            })}

            {processing && (
              <div className="flex items-center gap-2 ml-8 text-xs text-muted-foreground">
                <div className="w-3 h-3 border-2 border-signal-amber border-t-transparent rounded-full animate-spin" />
                Analyzing system state...
              </div>
            )}
          </div>

          <div className="glass-panel border-t border-white/[0.06] px-4 py-3 shrink-0">
            <div className="flex items-center gap-2">
              <Brain className="w-4 h-4 text-signal-amber shrink-0" />
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") handleSubmit(); }}
                placeholder="Ask about feed rankings, trust scores, policy impacts..."
                className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground outline-none font-mono"
                data-testid="operator-input"
              />
              <button
                onClick={handleSubmit}
                disabled={!query.trim() || processing}
                className={cn(
                  "p-2 rounded-md transition-colors",
                  query.trim() && !processing
                    ? "text-signal-amber hover:bg-white/[0.04]"
                    : "text-muted-foreground/30 cursor-not-allowed"
                )}
                data-testid="btn-operator-submit"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
