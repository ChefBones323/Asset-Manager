import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { ProposalCard } from "@/components/proposal-card";
import { LiveFeed } from "@/components/live-feed";
import { StatsBar } from "@/components/stats-bar";
import { StatusBadge } from "@/components/status-badge";
import { useToast } from "@/hooks/use-toast";
import { useTheme } from "@/components/theme-provider";
import type { Job } from "@shared/schema";
import {
  Brain,
  Send,
  LogOut,
  Moon,
  Sun,
  Sparkles,
  Shield,
  RefreshCw,
} from "lucide-react";
import { useLocation } from "wouter";

export default function DashboardPage() {
  const [intent, setIntent] = useState("");
  const { toast } = useToast();
  const { theme, toggleTheme } = useTheme();
  const [, setLocation] = useLocation();

  const { data: jobs = [], isLoading } = useQuery<Job[]>({
    queryKey: ["/api/jobs"],
    refetchInterval: 3000,
  });

  const createMutation = useMutation({
    mutationFn: async (intentText: string) => {
      const res = await apiRequest("POST", "/api/jobs", { intent: intentText });
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/jobs"] });
      setIntent("");
      toast({ title: "Proposal Generated", description: "Review the plan below and approve to execute." });
    },
    onError: () => {
      toast({ title: "Error", description: "Failed to generate proposal.", variant: "destructive" });
    },
  });

  const logoutMutation = useMutation({
    mutationFn: () => apiRequest("POST", "/api/auth/logout"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/auth/me"] });
      setLocation("/login");
    },
  });

  const awaitingJobs = jobs.filter((j) => j.status === "awaiting_approval");
  const approvedJobs = jobs.filter((j) => j.status === "approved");
  const runningJob = jobs.find((j) => j.status === "running") || null;
  const pausedJobs = jobs.filter((j) => j.status === "paused");
  const escalatedJobs = jobs.filter((j) => j.status === "escalated");
  const completedJobs = jobs.filter((j) => j.status === "completed" || j.status === "failed" || j.status === "cancelled");

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-6xl mx-auto flex items-center justify-between gap-2 px-4 py-3">
          <div className="flex items-center gap-2.5">
            <div className="flex items-center justify-center w-8 h-8 rounded-md bg-primary/10 border border-primary/20">
              <Brain className="w-4 h-4 text-primary" />
            </div>
            <div>
              <h1 className="text-sm font-semibold leading-none" data-testid="text-header-title">Control Plane</h1>
              <p className="text-xs text-muted-foreground mt-0.5">Human-supervised execution</p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <Button
              size="icon"
              variant="ghost"
              onClick={() => queryClient.invalidateQueries({ queryKey: ["/api/jobs"] })}
              data-testid="button-refresh"
            >
              <RefreshCw className="w-4 h-4" />
            </Button>
            <Button
              size="icon"
              variant="ghost"
              onClick={toggleTheme}
              data-testid="button-theme"
            >
              {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </Button>
            <Button
              size="icon"
              variant="ghost"
              onClick={() => logoutMutation.mutate()}
              data-testid="button-logout"
            >
              <LogOut className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-6 space-y-6">
        <Card>
          <CardContent className="pt-5 pb-5">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (intent.trim()) createMutation.mutate(intent.trim());
              }}
              className="space-y-3"
              data-testid="form-create-proposal"
            >
              <div className="flex items-center gap-2 mb-1">
                <Sparkles className="w-4 h-4 text-primary" />
                <span className="text-sm font-medium">New Proposal</span>
              </div>
              <div className="flex gap-2">
                <Input
                  value={intent}
                  onChange={(e) => setIntent(e.target.value)}
                  placeholder="Describe your high-level goal..."
                  className="flex-1"
                  data-testid="input-intent"
                />
                <Button
                  type="submit"
                  disabled={createMutation.isPending || !intent.trim()}
                  data-testid="button-generate"
                >
                  {createMutation.isPending ? (
                    "Generating..."
                  ) : (
                    <>
                      <Send className="w-4 h-4 mr-1" />
                      Generate
                    </>
                  )}
                </Button>
              </div>
              <p className="text-xs text-muted-foreground flex items-center gap-1">
                <Shield className="w-3 h-3" />
                Proposals require explicit approval before execution
              </p>
            </form>
          </CardContent>
        </Card>

        {isLoading ? (
          <div className="space-y-4">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-48 w-full" />
          </div>
        ) : (
          <>
            <StatsBar jobs={jobs} />

            <LiveFeed runningJob={runningJob} />

            <Tabs defaultValue="pending" className="space-y-4">
              <TabsList data-testid="tabs-jobs">
                <TabsTrigger value="pending" data-testid="tab-pending">
                  Pending
                  {awaitingJobs.length > 0 && (
                    <span className="ml-1.5 inline-flex items-center justify-center w-5 h-5 rounded-full bg-primary/20 text-primary text-xs font-medium">
                      {awaitingJobs.length}
                    </span>
                  )}
                </TabsTrigger>
                <TabsTrigger value="queued" data-testid="tab-queued">
                  Queued
                  {approvedJobs.length > 0 && (
                    <span className="ml-1.5 inline-flex items-center justify-center w-5 h-5 rounded-full bg-primary/20 text-primary text-xs font-medium">
                      {approvedJobs.length}
                    </span>
                  )}
                </TabsTrigger>
                <TabsTrigger value="governance" data-testid="tab-governance">
                  Governance
                  {(pausedJobs.length + escalatedJobs.length) > 0 && (
                    <span className="ml-1.5 inline-flex items-center justify-center w-5 h-5 rounded-full bg-orange-500/20 text-orange-500 text-xs font-medium">
                      {pausedJobs.length + escalatedJobs.length}
                    </span>
                  )}
                </TabsTrigger>
                <TabsTrigger value="history" data-testid="tab-history">
                  History
                </TabsTrigger>
                <TabsTrigger value="all" data-testid="tab-all">
                  All
                </TabsTrigger>
              </TabsList>

              <TabsContent value="pending" className="space-y-3">
                {awaitingJobs.length === 0 ? (
                  <EmptyState message="No proposals awaiting approval" />
                ) : (
                  awaitingJobs.map((job) => <ProposalCard key={job.id} job={job} />)
                )}
              </TabsContent>

              <TabsContent value="queued" className="space-y-3">
                {approvedJobs.length === 0 ? (
                  <EmptyState message="No jobs in the execution queue" />
                ) : (
                  approvedJobs.map((job) => <ProposalCard key={job.id} job={job} />)
                )}
              </TabsContent>

              <TabsContent value="governance" className="space-y-3">
                {pausedJobs.length === 0 && escalatedJobs.length === 0 ? (
                  <EmptyState message="No paused or escalated jobs requiring attention" />
                ) : (
                  [...escalatedJobs, ...pausedJobs].map((job) => <ProposalCard key={job.id} job={job} />)
                )}
              </TabsContent>

              <TabsContent value="history" className="space-y-3">
                {completedJobs.length === 0 ? (
                  <EmptyState message="No completed or failed jobs yet" />
                ) : (
                  completedJobs.map((job) => <ProposalCard key={job.id} job={job} />)
                )}
              </TabsContent>

              <TabsContent value="all" className="space-y-3">
                {jobs.length === 0 ? (
                  <EmptyState message="No jobs created yet. Generate your first proposal above." />
                ) : (
                  jobs.map((job) => <ProposalCard key={job.id} job={job} />)
                )}
              </TabsContent>
            </Tabs>
          </>
        )}
      </main>

      <footer className="border-t mt-12">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between text-xs text-muted-foreground">
          <span>Human = Final Authority</span>
          <span>Transparency is Alignment</span>
        </div>
      </footer>
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex items-center justify-center py-12 text-muted-foreground" data-testid="text-empty-state">
      <p className="text-sm">{message}</p>
    </div>
  );
}
