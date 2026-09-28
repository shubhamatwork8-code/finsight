import type { ReactNode } from "react";
import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  CircleDollarSign,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

export function AuthPageLayout({
  title,
  description,
  children,
  footer,
}: {
  title: string;
  description: string;
  children: ReactNode;
  footer: ReactNode;
}) {
  return (
    <main className="min-h-screen bg-[#090e19] text-white lg:grid lg:grid-cols-[1.1fr_0.9fr]">
      <section className="relative hidden min-h-screen flex-col justify-between overflow-hidden border-r border-white/[0.07] bg-[radial-gradient(ellipse_at_18%_25%,rgba(91,83,213,0.27),transparent_42%),radial-gradient(ellipse_at_70%_90%,rgba(20,177,147,0.09),transparent_48%),#0a101b] px-10 py-9 lg:flex xl:px-[8.5%]">
        <div className="pointer-events-none absolute -left-36 top-32 h-96 w-96 rounded-full bg-violet-600/10 blur-[110px]" />
        <div className="pointer-events-none absolute -bottom-32 right-0 h-96 w-96 rounded-full bg-emerald/10 blur-[110px]" />

        <div className="relative z-10 flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-500 shadow-[0_8px_30px_rgba(111,91,240,0.35)]">
            <Sparkles size={23} strokeWidth={1.8} />
          </div>
          <span className="text-[22px] font-semibold tracking-tight">FinSight</span>
        </div>

        <div className="relative z-10 mx-auto w-full max-w-[510px] py-10">
          <div className="rounded-[26px] border border-white/[0.09] bg-[#151d2d]/85 p-6 shadow-[0_28px_90px_rgba(0,0,0,0.35)] backdrop-blur-xl sm:p-8">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
                  Illustrative preview
                </p>
                <h2 className="mt-2 text-xl font-semibold">Risk overview</h2>
              </div>
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald/10 text-emerald">
                <Activity size={22} />
              </div>
            </div>

            <div className="mt-7 flex items-end justify-between gap-4">
              <div>
                <p className="text-sm text-slate-400">Portfolio visibility</p>
                <p className="mt-1 text-3xl font-semibold tracking-tight">At a glance</p>
              </div>
              <span className="mb-1 inline-flex items-center gap-1 rounded-full border border-emerald/20 bg-emerald/[0.08] px-2.5 py-1 text-xs font-medium text-emerald">
                <ArrowUpRight size={14} />
                Explainable
              </span>
            </div>

            <div className="mt-7 rounded-2xl border border-white/[0.06] bg-[#0e1624] p-4">
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-300">Transaction monitoring</span>
                <span className="font-medium text-white">Rule-based insights</span>
              </div>
              <div className="mt-4 flex h-2 gap-1 overflow-hidden rounded-full bg-white/[0.07]">
                <span className="w-[58%] rounded-full bg-gradient-to-r from-indigo-400 to-violet-400" />
                <span className="w-[26%] rounded-full bg-emerald/80" />
                <span className="flex-1 rounded-full bg-amber/70" />
              </div>
              <div className="mt-3 flex justify-between text-xs text-slate-500">
                <span>Ledger-backed activity</span>
                <span>Risk signals</span>
              </div>
            </div>

            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <div className="flex items-center gap-3 rounded-2xl border border-white/[0.06] bg-white/[0.025] p-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-400/10 text-indigo-300">
                  <CircleDollarSign size={19} />
                </div>
                <div>
                  <p className="text-sm font-medium">Balanced ledger</p>
                  <p className="mt-0.5 text-xs text-slate-500">Trace every posting</p>
                </div>
              </div>
              <div className="flex items-center gap-3 rounded-2xl border border-white/[0.06] bg-white/[0.025] p-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-emerald/10 text-emerald">
                  <ShieldCheck size={19} />
                </div>
                <div>
                  <p className="text-sm font-medium">Review with context</p>
                  <p className="mt-0.5 text-xs text-slate-500">Understand each alert</p>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-8 max-w-[470px]">
            <h2 className="text-xl font-semibold tracking-tight sm:text-[22px]">
              Clarity for every transaction.
            </h2>
            <p className="mt-2 text-sm leading-6 text-slate-400 sm:text-[15px]">
              Follow the money from ledger entry to risk signal, with the context your team needs to make informed decisions.
            </p>
          </div>
        </div>

        <p className="relative z-10 text-xs text-slate-500">
          Financial intelligence, made explainable.
        </p>
      </section>

      <section className="relative flex min-h-screen items-center justify-center overflow-hidden px-5 py-10 sm:px-8 lg:px-10 xl:px-16">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_50%_0%,rgba(91,83,213,0.12),transparent_44%)] lg:hidden" />
        <div className="relative z-10 w-full max-w-[440px]">
          <div className="mb-9 flex items-center gap-3 lg:hidden">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 to-indigo-500">
              <Sparkles size={20} />
            </div>
            <span className="text-lg font-semibold">FinSight</span>
          </div>

          <header className="mb-8">
            <h1 className="text-3xl font-semibold tracking-tight sm:text-[36px]">{title}</h1>
            <p className="mt-3 text-[15px] leading-6 text-slate-400">{description}</p>
          </header>

          {children}
          <div className="mt-8 text-center text-sm text-slate-400">{footer}</div>
          <p className="mt-9 text-center text-xs text-slate-600">
            Secure access to your FinSight workspace
          </p>
        </div>
      </section>
    </main>
  );
}

export function AuthSubmitButton({
  children,
  disabled,
}: {
  children: ReactNode;
  disabled: boolean;
}) {
  return (
    <button
      type="submit"
      disabled={disabled}
      className="mt-2 flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-500 px-5 py-4 text-[15px] font-semibold text-white shadow-[0_8px_25px_rgba(99,102,241,0.22)] transition hover:bg-indigo-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-300 disabled:cursor-not-allowed disabled:opacity-60"
    >
      {children}
      {!disabled ? <ArrowRight size={18} /> : null}
    </button>
  );
}
