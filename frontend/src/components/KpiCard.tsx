import type { ReactNode } from "react";

export function KpiCard({
  label,
  value,
  secondary,
  icon,
}: {
  label: string;
  value: string;
  secondary: string;
  icon: ReactNode;
}) {
  return (
    <article className="rounded-xl border border-line bg-panel p-4 shadow-card">
      <div className="flex items-start justify-between gap-3">
        <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted">{label}</p>
        <span className="text-signal">{icon}</span>
      </div>
      <p className="mt-4 font-mono text-2xl text-white">{value}</p>
      <p className="mt-1 text-sm text-muted">{secondary}</p>
    </article>
  );
}

export function RiskBadge({ level, score }: { level: string; score?: number }) {
  const styles: Record<string, string> = {
    LOW: "bg-emerald/15 text-emerald",
    MEDIUM: "bg-amber/15 text-amber",
    HIGH: "bg-coral/15 text-coral",
  };
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${styles[level] || styles.LOW}`}>
      {level}
      {score !== undefined ? <span className="font-mono">{score}</span> : null}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    POSTED: "text-emerald",
    ACTIVE: "text-emerald",
    UNDER_REVIEW: "text-amber",
    OPEN: "text-amber",
    RESOLVED: "text-signal",
    FALSE_POSITIVE: "text-muted",
    INACTIVE: "text-muted",
  };
  return <span className={`text-xs font-medium uppercase tracking-wide ${styles[status] || "text-muted"}`}>{status.replaceAll("_", " ")}</span>;
}
