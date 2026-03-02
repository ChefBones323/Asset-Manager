import { useEffect, useRef } from "react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Job } from "@shared/schema";
import { Radio, Terminal } from "lucide-react";

export function LiveFeed({ runningJob }: { runningJob: Job | null }) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [runningJob?.logs]);

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-1">
          <div className="flex items-center gap-2">
            <Terminal className="w-4 h-4 text-muted-foreground" />
            <span className="text-sm font-medium">Live Execution Feed</span>
          </div>
          {runningJob ? (
            <Badge variant="default" data-testid="badge-live">
              <Radio className="w-3 h-3 mr-1 animate-pulse" />
              Live
            </Badge>
          ) : (
            <Badge variant="secondary" data-testid="badge-idle">Idle</Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div
          ref={scrollRef}
          className="bg-background rounded-md p-4 h-48 overflow-y-auto font-mono text-xs"
          data-testid="container-live-feed"
        >
          {runningJob ? (
            <>
              <div className="text-muted-foreground mb-2">
                [{new Date(runningJob.approvedAt || runningJob.createdAt || "").toLocaleTimeString()}] Executing: {runningJob.intent}
              </div>
              {runningJob.logs ? (
                <pre className="text-chart-2 whitespace-pre-wrap">{runningJob.logs}</pre>
              ) : (
                <div className="text-muted-foreground flex items-center gap-2">
                  <span className="inline-block w-2 h-2 bg-primary rounded-full animate-pulse" />
                  Awaiting worker output...
                </div>
              )}
            </>
          ) : (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              <div className="text-center space-y-2">
                <Terminal className="w-6 h-6 mx-auto opacity-50" />
                <p>No active execution. Approve a proposal to begin.</p>
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
