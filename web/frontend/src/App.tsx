import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";

import { AuthProvider, useAuth } from "@/auth/AuthContext";
import { ProtectedRoute } from "@/auth/ProtectedRoute";
import { Button } from "@/components/ui";
import ChatPage from "@/pages/ChatPage";
import LoginPage from "@/pages/LoginPage";
import AgentsPage from "@/pages/admin/AgentsPage";
import UsersPage from "@/pages/admin/UsersPage";

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <AppShell />
            </ProtectedRoute>
          }
        />
      </Routes>
    </AuthProvider>
  );
}

function AppShell() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const isAdmin = user?.role === "admin";

  const tab = (to: string, label: string) => (
    <Link
      to={to}
      className={`rounded px-3 py-1.5 text-sm font-medium transition ${
        location.pathname.startsWith(to)
          ? "bg-slate-900 text-white"
          : "text-slate-600 hover:bg-slate-100"
      }`}
    >
      {label}
    </Link>
  );

  return (
    <div className="flex h-screen flex-col bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white px-6 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-6">
            <Link to="/chat" className="text-lg font-semibold tracking-tight">
              Flowcase
            </Link>
            <nav className="flex gap-1">
              {tab("/chat", "Chat")}
              {isAdmin && tab("/admin/agents", "Agenter")}
              {isAdmin && tab("/admin/users", "Brukere")}
            </nav>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <span className="text-slate-600">{user?.email}</span>
            <Button variant="secondary" size="sm" onClick={() => void logout()}>
              Logg ut
            </Button>
          </div>
        </div>
      </header>
      <main className="flex flex-1 overflow-hidden">
        <Routes>
          <Route path="/" element={<Navigate to="/chat" replace />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route
            path="/admin/agents"
            element={
              <ProtectedRoute requireAdmin>
                <AgentsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/users"
            element={
              <ProtectedRoute requireAdmin>
                <UsersPage />
              </ProtectedRoute>
            }
          />
        </Routes>
      </main>
    </div>
  );
}
