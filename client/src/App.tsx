import { Switch, Route, Redirect } from "wouter";
import { queryClient } from "./lib/queryClient";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ThemeProvider } from "@/components/theme-provider";
import { useAuth } from "@/hooks/use-auth";
import { CommandPalette } from "@/components/palette/CommandPalette";
import { SocialComposer } from "@/components/compose/SocialComposer";
import { AgentTaskModal } from "@/components/ai/AgentTaskModal";
import { AppShell } from "@/components/layout/AppShell";
import NotFound from "@/pages/not-found";
import LoginPage from "@/pages/login";
import MissionControl from "@/pages/MissionControl";
import GovernanceConsole from "@/pages/GovernanceConsole";
import FeedDebugger from "@/pages/FeedDebugger";
import TrustGraphView from "@/pages/TrustGraphView";
import EventExplorer from "@/pages/EventExplorer";
import SystemTimeline from "@/pages/SystemTimeline";
import AIOperator from "@/pages/AIOperator";
import SettingsPage from "@/pages/SettingsPage";

function AuthenticatedApp() {
  return (
    <AppShell>
      <Switch>
        <Route path="/" component={() => <Redirect to="/dashboard" />} />
        <Route path="/dashboard" component={MissionControl} />
        <Route path="/governance" component={GovernanceConsole} />
        <Route path="/feed" component={FeedDebugger} />
        <Route path="/trust" component={TrustGraphView} />
        <Route path="/events" component={EventExplorer} />
        <Route path="/timeline" component={SystemTimeline} />
        <Route path="/ai-operator" component={AIOperator} />
        <Route path="/settings" component={SettingsPage} />
        <Route component={NotFound} />
      </Switch>
    </AppShell>
  );
}

function AppGate() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center space-y-3">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-sm text-muted-foreground">Initializing control plane...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  return <AuthenticatedApp />;
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <TooltipProvider>
          <Toaster />
          <CommandPalette />
          <SocialComposer />
          <AgentTaskModal />
          <AppGate />
        </TooltipProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;
