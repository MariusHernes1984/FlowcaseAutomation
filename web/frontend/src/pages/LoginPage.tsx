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
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-zinc-50 px-6">
      {/* Soft brand backdrop */}
      <div
        aria-hidden
        className="absolute inset-0 -z-10 bg-gradient-to-br from-atea-50 via-white to-zinc-100"
      />
      <div
        aria-hidden
        className="absolute -top-40 left-1/2 -z-10 h-[480px] w-[480px] -translate-x-1/2 rounded-full bg-atea-600/15 blur-3xl"
      />

      <Card className="w-full max-w-md animate-fade-in p-8">
        <div className="mb-6 flex items-center gap-3">
          <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-atea-600 text-base font-bold text-white shadow-soft">
            F
          </span>
          <div>
            <h1 className="text-xl font-semibold tracking-tight">Flowcase</h1>
            <p className="text-xs text-zinc-500">Atea konsulent-søk</p>
          </div>
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
              className="mt-1.5"
              placeholder="du@atea.no"
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
              className="mt-1.5"
              placeholder="••••••••"
            />
          </div>
          {error && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
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
