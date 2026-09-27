import { FormEvent, useEffect, useState } from "react";
import { settingsApi } from "../api";
import { errorMessage } from "../api/client";
import { useLedgerCurrency } from "../components/Currency";
import { controlClass } from "../components/Modal";
import { ErrorState, LoadingState } from "../components/States";
import { RiskBadge } from "../components/KpiCard";
import { Button, Topbar } from "../components/Topbar";
import type { RiskSettings } from "../types";

const currencies = [
  ["USD", "US dollar"],
  ["EUR", "Euro"],
  ["GBP", "British pound"],
  ["INR", "Indian rupee"],
  ["AED", "UAE dirham"],
  ["SGD", "Singapore dollar"],
  ["AUD", "Australian dollar"],
  ["CAD", "Canadian dollar"],
  ["CHF", "Swiss franc"],
  ["JPY", "Japanese yen"],
];

function clock(hour: number) {
  return `${String(hour).padStart(2, "0")}:00`;
}

const fields: { key: keyof RiskSettings; label: string }[] = [
  { key: "duplicate_window_minutes", label: "Duplicate window (minutes)" },
  { key: "duplicate_score", label: "Duplicate score" },
  { key: "frequency_threshold", label: "Frequency count" },
  { key: "frequency_window_minutes", label: "Frequency window (minutes)" },
  { key: "frequency_score", label: "Frequency score" },
  { key: "large_multiplier_medium", label: "Large amount multiplier (medium)" },
  { key: "large_multiplier_high", label: "Large amount multiplier (high)" },
  { key: "large_score_medium", label: "Large amount score (medium)" },
  { key: "large_score_high", label: "Large amount score (high)" },
  { key: "unusual_start_hour", label: "Unusual hours start" },
  { key: "unusual_end_hour", label: "Unusual hours end" },
  { key: "unusual_time_score", label: "Unusual time score" },
  { key: "anomaly_score", label: "Historical anomaly score" },
  { key: "min_history_count", label: "Minimum history count" },
  { key: "alert_threshold", label: "Alert threshold" },
];

export function Settings() {
  const { setCode } = useLedgerCurrency();
  const [settings, setSettings] = useState<RiskSettings | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [saved, setSaved] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  function load() {
    setLoading(true);
    settingsApi
      .get()
      .then((row) => {
        setSettings(row);
        setError(null);
      })
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
  }, []);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!settings) return;
    setSaving(true);
    setSaved(null);
    setFormError(null);
    try {
      const payload = (await settingsApi.update(settings)) as RiskSettings & {
        conversion?: { from: string; to: string; rate: string };
      };
      const conversion = payload.conversion;
      const next = { ...payload };
      delete next.conversion;
      setSettings(next);
      setCode(next.ledger_currency);
      setSaved(
        conversion
          ? `Amounts converted from ${conversion.from} to ${conversion.to} at ${conversion.rate}.`
          : "Thresholds saved.",
      );
    } catch (err) {
      setFormError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <LoadingState label="Loading settings" />;
  if (error || !settings) return <ErrorState message={error || "Settings unavailable"} onRetry={load} />;

  return (
    <div>
      <Topbar
        eyebrow="Risk configuration"
        title="Settings"
        subtitle="These rules are what the engine actually applies. The numbers below are live thresholds, and saving them changes the next evaluation."
      />
      <section className="mb-8 max-w-3xl">
        <h2 className="text-xl font-semibold">Fraud detection rules</h2>
        <p className="mt-2 text-sm leading-6 text-muted">
          Every customer transaction is scored from 0 to 100 by adding the points for each rule that fires. The score is capped at 100. Opening-balance postings are excluded from history and are not scored. This is a rule engine, not a machine-learning model.
        </p>
        <div className="mt-4 flex flex-wrap gap-2 text-sm">
          <span className="rounded-full border border-line px-3 py-1">
            <RiskBadge level="LOW" /> 0–29 · posted, no alert
          </span>
          <span className="rounded-full border border-line px-3 py-1">
            <RiskBadge level="MEDIUM" /> 30–69 · under review
          </span>
          <span className="rounded-full border border-line px-3 py-1">
            <RiskBadge level="HIGH" /> 70–100 · under review
          </span>
        </div>
        <p className="mt-3 text-sm text-muted">
          An alert opens when the score reaches {settings.alert_threshold}. Resolving an alert does not erase the original score.
        </p>
        <ol className="mt-4 space-y-3">
          <Rule
            name="Duplicate transaction"
            points={`+${settings.duplicate_score}`}
            body={`Same account, same merchant, and the same amount within ${settings.duplicate_window_minutes} minutes.`}
          />
          <Rule
            name="Large transaction"
            points={`+${settings.large_score_medium} or +${settings.large_score_high}`}
            body={`Compared with this account's own average, after at least ${settings.min_history_count} earlier transactions. ${settings.large_multiplier_medium}× the average adds ${settings.large_score_medium} points. ${settings.large_multiplier_high}× the average adds ${settings.large_score_high} points. There is no single global dollar cutoff.`}
          />
          <Rule
            name="High frequency"
            points={`+${settings.frequency_score}`}
            body={`${settings.frequency_threshold} or more transactions on the same account inside ${settings.frequency_window_minutes} minutes, including the one being scored.`}
          />
          <Rule
            name="Unusual time"
            points={`+${settings.unusual_time_score}`}
            body={`Posted between ${clock(settings.unusual_start_hour)} and ${clock(settings.unusual_end_hour)} UTC, and only when overnight activity is not already normal for that account. ${
              settings.unusual_time_score < settings.alert_threshold
                ? "At the current points it stays below the alert line unless another rule also fires."
                : "At the current points it can open an alert on its own."
            }`}
          />
          <Rule
            name="Historical anomaly"
            points={`+${settings.anomaly_score}`}
            body={`Needs at least ${settings.min_history_count} earlier transactions. It fires when the amount is more than 2 standard deviations above the account mean, or when the merchant is new and the amount is at least 2× the average.`}
          />
        </ol>
      </section>
      <h2 className="mb-3 text-xl font-semibold">Ledger currency</h2>
      <form onSubmit={onSubmit} className="grid max-w-3xl gap-3 md:grid-cols-2">
        <label className="text-sm md:col-span-2">
          <span className="mb-1 block text-muted">Operating currency</span>
          <select
            className={controlClass}
            value={settings.ledger_currency || "USD"}
            onChange={(event) => setSettings({ ...settings, ledger_currency: event.target.value })}
          >
            {currencies.map(([code, label]) => (
              <option key={code} value={code}>
                {code} — {label}
              </option>
            ))}
          </select>
          <span className="mt-2 block text-muted">
            One currency for the whole book. Saving a new choice converts every balance and posting at a published mid-market rate, then records that rate in the audit log. It is a reference rate, not a bank dealing rate.
          </span>
        </label>
        <h2 className="mt-4 text-xl font-semibold md:col-span-2">Thresholds</h2>
        {fields.map((field) => (
          <label key={field.key} className="text-sm">
            <span className="mb-1 block text-muted">{field.label}</span>
            <input
              type="number"
              className={controlClass}
              value={settings[field.key]}
              onChange={(event) => setSettings({ ...settings, [field.key]: Number(event.target.value) })}
            />
          </label>
        ))}
        {formError ? <p className="text-sm text-coral md:col-span-2">{formError}</p> : null}
        {saved ? <p className="text-sm text-emerald md:col-span-2">{saved}</p> : null}
        <Button type="submit" tone="primary" disabled={saving}>
          {saving ? "Saving…" : "Save thresholds"}
        </Button>
      </form>
    </div>
  );
}

function Rule({ name, points, body }: { name: string; points: string; body: string }) {
  return (
    <li className="rounded-lg border border-line bg-panel px-4 py-3">
      <div className="flex items-baseline justify-between gap-3">
        <h3 className="text-sm font-semibold">{name}</h3>
        <span className="font-mono text-xs text-emerald">{points}</span>
      </div>
      <p className="mt-1 text-sm leading-6 text-muted">{body}</p>
    </li>
  );
}
