import type { ReactNode } from "react";

export function Topbar({
  eyebrow,
  title,
  subtitle,
  actions,
}: {
  eyebrow: string;
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
      <div>
        <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-emerald">{eyebrow}</p>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight text-white md:text-4xl">{title}</h1>
        {subtitle ? <p className="mt-2 max-w-2xl text-sm text-muted">{subtitle}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
    </header>
  );
}

export function Button({
  children,
  tone = "secondary",
  type = "button",
  disabled,
  onClick,
}: {
  children: ReactNode;
  tone?: "primary" | "secondary" | "danger" | "ghost";
  type?: "button" | "submit";
  disabled?: boolean;
  onClick?: () => void;
}) {
  const tones = {
    primary: "bg-emerald text-ink hover:brightness-110",
    secondary: "border border-line bg-panel2 text-white hover:border-signal",
    danger: "border border-coral/40 bg-coral/10 text-coral hover:bg-coral/20",
    ghost: "text-muted hover:text-white",
  };
  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      className={`inline-flex items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50 ${tones[tone]}`}
    >
      {children}
    </button>
  );
}
