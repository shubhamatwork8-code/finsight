import { FormEvent, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { authApi } from "../api";
import { errorMessage } from "../api/client";
import { useAuth } from "../components/Auth";
import { AuthPageLayout, AuthSubmitButton } from "../components/AuthPageLayout";
import { LockKeyhole, Mail } from "lucide-react";

function AuthField({
  label,
  name,
  type,
  placeholder,
  autoComplete,
}: {
  label: string;
  name: string;
  type: string;
  placeholder: string;
  autoComplete: string;
}) {
  const Icon = type === "password" ? LockKeyhole : Mail;
  return (
    <label className="block text-sm font-medium text-slate-300">
      <span className="mb-2 block">{label}</span>
      <span className="flex items-center gap-3 rounded-xl border border-white/[0.09] bg-white/[0.035] px-4 transition focus-within:border-indigo-400/70 focus-within:bg-white/[0.055]">
        <Icon size={18} className="shrink-0 text-slate-500" aria-hidden="true" />
        <input
          name={name}
          type={type}
          required
          autoComplete={autoComplete}
          placeholder={placeholder}
          className="h-[54px] min-w-0 flex-1 bg-transparent text-[15px] text-white outline-none placeholder:text-slate-600"
        />
      </span>
    </label>
  );
}

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
    <AuthPageLayout
      title="Welcome back"
      description="Sign in to your account to continue."
      footer={
        <>
          Don&apos;t have an account?{" "}
          <Link className="font-semibold text-indigo-300 transition hover:text-indigo-200" to="/register">
            Sign up
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} className="grid gap-5">
        <AuthField
          label="Email address"
          name="email"
          type="email"
          autoComplete="username"
          placeholder="name@example.com"
        />
        <AuthField
          label="Password"
          name="password"
          type="password"
          autoComplete="current-password"
          placeholder="Enter your password"
        />

        {error ? (
          <p role="alert" className="rounded-xl border border-coral/25 bg-coral/10 p-3 text-sm text-coral">
            {error}
          </p>
        ) : null}

        <AuthSubmitButton disabled={saving}>
          {saving ? "Signing in..." : "Sign in"}
        </AuthSubmitButton>
      </form>
    </AuthPageLayout>
  );
}
