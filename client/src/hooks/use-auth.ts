import { useQuery, useMutation } from "@tanstack/react-query";
import { getQueryFn, apiRequest, queryClient } from "@/lib/queryClient";
import { useLocation } from "wouter";

export function useAuth() {
  const { data: user, isLoading } = useQuery<{ admin: boolean } | null>({
    queryKey: ["/api/auth/me"],
    queryFn: getQueryFn({ on401: "returnNull" }),
  });

  const [, navigate] = useLocation();

  const logoutMutation = useMutation({
    mutationFn: async () => {
      await apiRequest("POST", "/api/auth/logout");
    },
    onSuccess: () => {
      queryClient.setQueryData(["/api/auth/me"], null);
      navigate("/login");
    },
  });

  return {
    isAuthenticated: !!user?.admin,
    isLoading,
    logout: () => logoutMutation.mutate(),
  };
}
