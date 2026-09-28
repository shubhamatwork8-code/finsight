import { FormEvent, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { authApi } from "../api";
import { errorMessage } from "../api/client";
import { useAuth } from "../components/Auth";
import { AuthPageLayout, AuthSubmitButton } from "../components/AuthPageLayout";
import { LockKeyhole, Mail, UserRound } from "lucide-react";

function AuthField({
  label,
  name,
  type,
  placeholder,
  autoComplete,
  minLength,
}: {
  label: string;
  name: string;
  type: string;
  placeholder: string;
  autoComplete?: string;
  minLength?: number;
}) {
  const Icon = name === "full_name" ? UserRound : type === "password" ? LockKeyhole : Mail;
  return (
    <label className="block text-sm font-medium text-slate-300">
      <span className="mb-2 block">{label}</span>
      <span className="flex items-center gap-3 rounded-xl border border-white/[0.09] bg-white/[0.035] px-4 transition focus-within:border-indigo-400/70 focus-within:bg-white/[0.055]">
        <Icon size={18} className="shrink-0 text-slate-500" aria-hidden="true" />
        <input
          name={name}
          type={type}
          required
          minLength={minLength}
          autoComplete={autoComplete}
          placeholder={placeholder}
          className="h-[54px] min-w-0 flex-1 bg-transparent text-[15px] text-white outline-none placeholder:text-slate-600"
        />
      </span>
    </label>
  );
}

export function Register() {
  const { user, ready } = useAuth();
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
      await authApi.register({
        full_name: String(form.get("full_name") || ""),
        email: String(form.get("email") || ""),
        password: String(form.get("password") || ""),
      });
      navigate("/login");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <AuthPageLayout
      title="Create your account"
      description="Set up your FinSight workspace and start with a clear view of your ledger."
      footer={
        <>
          Already have an account?{" "}
          <Link className="font-semibold text-indigo-300 transition hover:text-indigo-200" to="/login">
            Sign in
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} className="grid gap-4">
        <AuthField
          label="Full name"
          name="full_name"
          type="text"
          autoComplete="name"
          placeholder="Your name"
        />
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
          minLength={8}
          autoComplete="new-password"
          placeholder="At least 8 characters"
        />

        {error ? (
          <p role="alert" className="rounded-xl border border-coral/25 bg-coral/10 p-3 text-sm text-coral">
            {error}
          </p>
        ) : null}

        <AuthSubmitButton disabled={saving}>
          {saving ? "Creating account..." : "Create account"}
        </AuthSubmitButton>
      </form>
    </AuthPageLayout>
  );
}
