import {
  BookUser,
  LogOut,
  MessagesSquare,
  ShieldCheck,
  Users,
} from "lucide-react";
import {
  Link,
  Navigate,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";

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

  const tab = (to: string, label: string, Icon: typeof MessagesSquare) => {
    const active = location.pathname.startsWith(to);
    return (
      <Link
        to={to}
        className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
          active
            ? "bg-zinc-900 text-white shadow-soft"
            : "text-zinc-600 hover:bg-zinc-100"
        }`}
      >
        <Icon className="h-3.5 w-3.5" strokeWidth={2.2} />
        {label}
      </Link>
    );
  };

  return (
    <div className="flex h-screen flex-col bg-zinc-50 text-zinc-900">
      <header className="border-b border-zinc-200/70 bg-white/80 px-6 py-3 backdrop-blur-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-6">
            <Link to="/chat" className="flex items-center gap-2">
              <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-atea-600 text-sm font-bold text-white shadow-soft">
                F
              </span>
              <span className="text-base font-semibold tracking-tight">
                Flowcase
              </span>
            </Link>
            <nav className="flex gap-1">
              {tab("/chat", "Chat", MessagesSquare)}
              {isAdmin && tab("/admin/agents", "Agenter", BookUser)}
              {isAdmin && tab("/admin/users", "Brukere", Users)}
            </nav>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <div className="hidden items-center gap-1.5 text-zinc-600 md:flex">
              <ShieldCheck className="h-3.5 w-3.5 text-zinc-400" />
              {user?.email}
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => void logout()}
              className="gap-1.5"
            >
              <LogOut className="h-3.5 w-3.5" />
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
