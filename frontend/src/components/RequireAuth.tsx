import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "./Auth";

export function RequireAuth({ children }: { children: ReactNode }) {
  const { user, ready } = useAuth();
  if (!ready) {
    return <div className="grid min-h-screen place-items-center text-sm text-muted">Checking session…</div>;
  }
  if (!user) return <Navigate to="/login" replace />;
  return children;
}
