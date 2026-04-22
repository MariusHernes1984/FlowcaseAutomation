import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "@/auth/AuthContext";
import type { ReactNode } from "react";

export function ProtectedRoute({
  children,
  requireAdmin = false,
}: {
  children: ReactNode;
  requireAdmin?: boolean;
}) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-slate-500">
        Laster…
      </div>
    );
  }
  if (!user) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }
  if (requireAdmin && user.role !== "admin") {
    return <Navigate to="/chat" replace />;
  }
  return <>{children}</>;
}
