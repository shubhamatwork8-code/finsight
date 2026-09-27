import { FormEvent, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { authApi } from "../api";
import { errorMessage } from "../api/client";
import { useAuth } from "../components/Auth";
import { Field, controlClass } from "../components/Modal";
import { Button } from "../components/Topbar";

export function Login() {
  const { user, ready, signIn } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  if (ready && user) return <Navigate to="/dashboard" replace />;

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setSaving(true);
    setError(null);
    try {
      const session = await authApi.login({
        email: String(form.get("email") || ""),
        password: String(form.get("password") || ""),
      });
      signIn(session.token, session.user);
      navigate("/dashboard");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="grid min-h-screen place-items-center bg-ink px-4">
      <form onSubmit={onSubmit} className="w-full max-w-md rounded-xl border border-line bg-navy p-6 shadow-card">
        <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-emerald">Workspace</p>
        <h1 className="mt-2 text-3xl font-semibold text-white">Sign in to FinSight</h1>
        <p className="mt-2 text-sm text-muted">Each login keeps its own ledger, risk settings, and audit trail.</p>
        <div className="mt-6 grid gap-3">
          <Field label="Email">
            <input name="email" type="email" required autoComplete="username" className={controlClass} />
          </Field>
          <Field label="Password">
            <input name="password" type="password" required autoComplete="current-password" className={controlClass} />
          </Field>
          {error ? <p className="text-sm text-coral">{error}</p> : null}
          <Button type="submit" tone="primary" disabled={saving}>
            {saving ? "Signing in…" : "Sign in"}
          </Button>
        </div>
        <p className="mt-4 text-sm text-muted">
          New here? <Link className="text-signal" to="/register">Create an account</Link>
        </p>
        <p className="mt-4 rounded-md border border-line bg-ink px-3 py-2 text-sm text-muted">
          Demo books: <span className="text-white">demo@finsight.local</span> / <span className="font-mono text-white">FinSight-demo-1</span>
        </p>
      </form>
    </div>
  );
}
