import { useState } from "react";
import { useLocation } from "wouter";
import { useMutation } from "@tanstack/react-query";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import { Shield, Lock, Brain, ArrowRight, Zap, Eye } from "lucide-react";

export default function LoginPage() {
  const [password, setPassword] = useState("");
  const [, setLocation] = useLocation();
  const { toast } = useToast();

  const loginMutation = useMutation({
    mutationFn: async (pwd: string) => {
      const res = await apiRequest("POST", "/api/auth/login", { password: pwd });
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/auth/me"] });
      setLocation("/");
    },
    onError: () => {
      toast({
        title: "Authentication Failed",
        description: "Invalid credentials. Access denied.",
        variant: "destructive",
      });
    },
  });

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center space-y-3">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-md bg-primary/10 border border-primary/20 mb-2">
            <Brain className="w-8 h-8 text-primary" />
          </div>
          <h1 className="text-2xl font-semibold tracking-tight" data-testid="text-title">
            Cognitive Control Plane
          </h1>
          <p className="text-sm text-muted-foreground max-w-xs mx-auto">
            Human-supervised execution environment. Authenticate to access the control interface.
          </p>
        </div>

        <Card>
          <CardContent className="pt-6 space-y-6">
            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              <div className="flex items-center gap-1.5">
                <Shield className="w-3.5 h-3.5 text-primary" />
                <span>Verified</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-chart-2" />
                <span>Encrypted</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Eye className="w-3.5 h-3.5 text-chart-3" />
                <span>Transparent</span>
              </div>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                loginMutation.mutate(password);
              }}
              className="space-y-4"
              data-testid="form-login"
            >
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="password">
                  Admin Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    id="password"
                    type="password"
                    placeholder="Enter admin password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="pl-10"
                    autoFocus
                    data-testid="input-password"
                  />
                </div>
              </div>

              <Button
                type="submit"
                className="w-full"
                disabled={loginMutation.isPending || !password}
                data-testid="button-login"
              >
                {loginMutation.isPending ? (
                  "Authenticating..."
                ) : (
                  <>
                    Authenticate
                    <ArrowRight className="w-4 h-4 ml-1" />
                  </>
                )}
              </Button>
            </form>

            <div className="pt-2 border-t">
              <div className="flex items-start gap-2 text-xs text-muted-foreground">
                <Shield className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                <p>
                  All actions require explicit human approval. No autonomous execution without consent.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <p className="text-center text-xs text-muted-foreground">
          Human = Final Authority &middot; Transparency is Alignment
        </p>
      </div>
    </div>
  );
}
