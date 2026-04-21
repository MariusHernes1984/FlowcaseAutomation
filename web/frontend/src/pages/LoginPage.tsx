import { useState, type FormEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "@/auth/AuthContext";
import { Button, Card, Input, Label } from "@/components/ui";

export default function LoginPage() {
  const { login, user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (user) {
    const from = (location.state as { from?: string })?.from ?? "/chat";
    navigate(from, { replace: true });
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(email, password);
      const from = (location.state as { from?: string })?.from ?? "/chat";
      navigate(from, { replace: true });
    } catch (err) {
      const message =
        (err as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail ?? "Feil ved innlogging";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-6">
      <Card className="w-full max-w-md p-8">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold tracking-tight">Flowcase</h1>
          <p className="mt-1 text-sm text-slate-500">
            Logg inn med brukernavn og passord
          </p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="email">E-post</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1"
            />
          </div>
          <div>
            <Label htmlFor="password">Passord</Label>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1"
            />
          </div>
          {error && (
            <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}
          <Button type="submit" disabled={submitting} className="w-full">
            {submitting ? "Logger inn…" : "Logg inn"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
