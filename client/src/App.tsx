import { Switch, Route } from "wouter";
import { queryClient } from "./lib/queryClient";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ThemeProvider } from "@/components/theme-provider";
import { useAuth } from "@/hooks/use-auth";
import { CommandPalette } from "@/components/palette/CommandPalette";
import NotFound from "@/pages/not-found";
import LoginPage from "@/pages/login";
import MissionControl from "@/pages/MissionControl";
import GovernanceConsole from "@/pages/GovernanceConsole";
import FeedDebugger from "@/pages/FeedDebugger";
import TrustGraphView from "@/pages/TrustGraphView";
import EventExplorer from "@/pages/EventExplorer";

function ProtectedRoute({ component: Component }: { component: () => JSX.Element }) {
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

  return <Component />;
}

function Router() {
  return (
    <Switch>
      <Route path="/" component={() => <ProtectedRoute component={MissionControl} />} />
      <Route path="/governance" component={() => <ProtectedRoute component={GovernanceConsole} />} />
      <Route path="/feed-debugger" component={() => <ProtectedRoute component={FeedDebugger} />} />
      <Route path="/trust-graph" component={() => <ProtectedRoute component={TrustGraphView} />} />
      <Route path="/events" component={() => <ProtectedRoute component={EventExplorer} />} />
      <Route path="/login" component={LoginPage} />
      <Route component={NotFound} />
    </Switch>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <TooltipProvider>
          <Toaster />
          <CommandPalette />
          <Router />
        </TooltipProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;
