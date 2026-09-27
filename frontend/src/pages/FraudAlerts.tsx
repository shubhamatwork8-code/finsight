import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { fraudApi } from "../api";
import { errorMessage } from "../api/client";
import { useMoney } from "../components/Currency";
import { RiskBadge, StatusBadge } from "../components/KpiCard";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { Button, Topbar } from "../components/Topbar";
import { when } from "../lib/format";
import type { FraudAlert } from "../types";

export function FraudAlerts() {
  const money = useMoney();
  const [params] = useSearchParams();
  const focus = params.get("alert");
  const [status, setStatus] = useState("");
  const [alerts, setAlerts] = useState<FraudAlert[]>([]);
  const [active, setActive] = useState<FraudAlert | null>(null);
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  function load() {
    setLoading(true);
    const query: Record<string, string | number> = { page: 1, page_size: 50 };
    if (status) query.status = status;
    fraudApi
      .list(query)
      .then((page) => {
        setAlerts(page.items);
        const match = page.items.find((item) => item.id === focus) || page.items[0] || null;
        setActive(match);
        setNote(match?.resolution_note || "");
        setError(null);
      })
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, focus]);

  async function review(nextStatus: string) {
    if (!active) return;
    setSaving(true);
    setFormError(null);
    try {
      const updated = await fraudApi.review(active.id, { status: nextStatus, resolution_note: note });
      setActive(updated);
      load();
    } catch (err) {
      setFormError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <Topbar
        eyebrow="Review queue"
        title="Fraud Alerts"
        subtitle="Alerts are created by the rule engine. Resolve them with a note, or mark a false positive."
      />
      <div className="mb-4">
        <label className="text-sm text-muted">
          Status
          <select value={status} onChange={(event) => setStatus(event.target.value)} className="ml-2 rounded-md border border-line bg-ink px-3 py-2">
            <option value="">All</option>
            <option>OPEN</option>
            <option>UNDER_REVIEW</option>
            <option>RESOLVED</option>
            <option>FALSE_POSITIVE</option>
          </select>
        </label>
      </div>
      {loading ? <LoadingState label="Loading alerts" /> : null}
      {error ? <ErrorState message={error} onRetry={load} /> : null}
      {!loading && !error && alerts.length === 0 ? <EmptyState title="No alerts" body="The engine will open an alert when a score reaches the review threshold." /> : null}
      {!loading && alerts.length > 0 ? (
        <div className="grid gap-4 lg:grid-cols-[320px_1fr]">
          <div className="space-y-2">
            {alerts.map((alert) => (
              <button
                key={alert.id}
                onClick={() => {
                  setActive(alert);
                  setNote(alert.resolution_note);
                }}
                className={`w-full rounded-lg border p-3 text-left ${active?.id === alert.id ? "border-signal bg-panel" : "border-line bg-panel/60"}`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium uppercase">{alert.alert_type.replaceAll("_", " ")}</span>
                  <RiskBadge level={alert.risk_level} score={alert.risk_score} />
                </div>
                <p className="mt-2 text-sm">{alert.merchant}</p>
                <p className="text-xs text-muted">{money(alert.amount)} · {alert.account_name}</p>
              </button>
            ))}
          </div>
          {active ? (
            <article className="rounded-xl border border-line bg-panel p-5">
              <div className="flex flex-wrap items-center gap-3">
                <h2 className="text-xl font-semibold">{active.id}</h2>
                <StatusBadge status={active.status} />
              </div>
              <p className="mt-2 text-sm text-muted">
                {active.transaction_id} · {active.account_name} · {when(active.created_at)}
              </p>
              <p className="mt-4 text-sm font-medium">{active.rule_summary || "No rule was triggered"}</p>
              <p className="mt-2 text-sm leading-6">{active.explanation}</p>
              <p className="mt-3 text-sm text-muted">
                Hybrid {active.risk_score}
                {active.rule_score != null ? ` · Rules ${active.rule_score}` : ""}
                {active.ml_score != null ? ` · Model ${active.ml_score}` : ""}
              </p>
              <ul className="mt-4 space-y-2">
                {active.triggered_rules.map((rule) => (
                  <li key={rule.code} className="rounded-md border border-line px-3 py-2 text-sm">
                    {rule.explanation} <span className="font-mono text-muted">+{rule.points}</span>
                  </li>
                ))}
              </ul>
              {active.reviews.length > 0 ? (
                <div className="mt-4 space-y-2">
                  <h3 className="text-sm font-medium">Review history</h3>
                  {active.reviews.map((review) => (
                    <p key={review.id} className="text-sm text-muted">
                      {review.reviewer_name} · {when(review.created_at)} · {review.from_status} to {review.to_status}
                      {review.note ? ` · ${review.note}` : ""}
                    </p>
                  ))}
                </div>
              ) : null}
              <label className="mt-4 block text-sm">
                <span className="mb-1 block text-muted">Resolution note</span>
                <textarea value={note} onChange={(event) => setNote(event.target.value)} rows={3} className="w-full rounded-md border border-line bg-ink px-3 py-2" />
              </label>
              {formError ? <p className="mt-2 text-sm text-coral">{formError}</p> : null}
              <div className="mt-4 flex flex-wrap gap-2">
                <Button disabled={saving} onClick={() => review("UNDER_REVIEW")}>Mark reviewed</Button>
                <Button disabled={saving} tone="primary" onClick={() => review("RESOLVED")}>Mark resolved</Button>
                <Button disabled={saving} tone="danger" onClick={() => review("FALSE_POSITIVE")}>False positive</Button>
              </div>
            </article>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
