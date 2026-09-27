import { useEffect, useState } from "react";
import { ArrowLeftRight, ShieldAlert, Upload, Wallet } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { dashboardApi } from "../api";
import { errorMessage } from "../api/client";
import { useMoney } from "../components/Currency";
import { KpiCard, RiskBadge, StatusBadge } from "../components/KpiCard";
import { Button, Topbar } from "../components/Topbar";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { shortDate, when } from "../lib/format";
import type { DashboardSummary } from "../types";

export function Dashboard() {
  const money = useMoney();
  const navigate = useNavigate();
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  function load() {
    setLoading(true);
    dashboardApi
      .summary()
      .then(setData)
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
  }, []);

  if (loading) return <LoadingState label="Loading dashboard" />;
  if (error || !data) return <ErrorState message={error || "Dashboard unavailable"} onRetry={load} />;

  const series = data.volume_series.map((point) => ({ date: shortDate(point.date), amount: Number(point.amount) }));
  const risk = ["LOW", "MEDIUM", "HIGH"].map((level) => ({ level, count: data.risk_distribution[level] || 0 }));
  const maxRisk = Math.max(1, ...risk.map((item) => item.count));

  return (
    <div>
      <Topbar
        eyebrow="Executive fraud & ledger overview"
        title="FinSight Dashboard"
        subtitle="Real-time transaction intelligence, double-entry ledger monitoring, and explainable risk scoring."
        actions={
          <>
            <Button onClick={() => navigate("/transactions?import=1")}>
              <Upload size={16} /> Import CSV
            </Button>
            <Button onClick={() => navigate("/transactions?receipt=1")}>Import receipt</Button>
            <Button onClick={() => navigate("/accounts?create=1")}>New Account</Button>
            <Button tone="primary" onClick={() => navigate("/transactions?record=1")}>
              Record Transaction
            </Button>
          </>
        }
      />
      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Total account balance" value={money(data.total_balance)} secondary="Across all active accounts" icon={<Wallet size={18} />} />
        <KpiCard label="Active accounts" value={String(data.active_accounts)} secondary="Currently active" icon={<Wallet size={18} />} />
        <KpiCard
          label="Transaction volume"
          value={money(data.transaction_volume)}
          secondary={`${data.transaction_count} total records`}
          icon={<ArrowLeftRight size={18} />}
        />
        <KpiCard
          label="Open fraud alerts"
          value={String(data.open_alerts)}
          secondary={`${data.high_risk_alerts} high-risk ${data.high_risk_alerts === 1 ? "alert" : "alerts"}`}
          icon={<ShieldAlert size={18} />}
        />
      </section>
      <section className="mt-4 grid gap-4 xl:grid-cols-5">
        <article className="rounded-xl border border-line bg-panel p-4 xl:col-span-3">
          <h2 className="text-lg font-semibold">Transaction activity</h2>
          <p className="mb-4 text-sm text-muted">Posted volume by day, excluding opening balances</p>
          {series.length === 0 ? (
            <EmptyState title="No activity yet" body="Record a transaction to populate this chart." />
          ) : (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={series}>
                  <CartesianGrid stroke="#243454" vertical={false} />
                  <XAxis dataKey="date" stroke="#93a4c3" fontSize={12} />
                  <YAxis stroke="#93a4c3" fontSize={12} />
                  <Tooltip formatter={(value) => money(Number(value))} />
                  <Area type="monotone" dataKey="amount" name="Volume" stroke="#3ddc97" fill="#3ddc9733" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </article>
        <article className="rounded-xl border border-line bg-panel p-4 xl:col-span-2">
          <h2 className="text-lg font-semibold">Risk distribution</h2>
          <p className="mb-4 text-sm text-muted">Transactions by explainable risk level</p>
          <div className="space-y-4">
            {risk.map((item) => (
              <div key={item.level}>
                <div className="mb-1 flex justify-between text-sm">
                  <RiskBadge level={item.level} />
                  <span className="font-mono text-muted">{item.count}</span>
                </div>
                <div className="h-2 rounded-full bg-ink">
                  <div
                    className={`h-2 rounded-full ${item.level === "HIGH" ? "bg-coral" : item.level === "MEDIUM" ? "bg-amber" : "bg-emerald"}`}
                    style={{ width: `${(item.count / maxRisk) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </article>
      </section>
      <section className="mt-4 grid gap-4 xl:grid-cols-5">
        <article className="rounded-xl border border-line bg-panel p-4 xl:col-span-3">
          <h2 className="mb-3 text-lg font-semibold">Recent ledger transactions</h2>
          {data.recent_transactions.length === 0 ? (
            <EmptyState title="No transactions" body="Activity will appear here after the first posting." />
          ) : (
            <div className="table-wrap">
              <table className="w-full min-w-[680px] text-left text-sm">
                <thead className="text-xs uppercase tracking-wide text-muted">
                  <tr>
                    <th className="py-2 font-medium">Timestamp</th>
                    <th className="font-medium">Merchant / category</th>
                    <th className="font-medium">Type</th>
                    <th className="font-medium">Amount</th>
                    <th className="font-medium">Risk</th>
                    <th className="font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {data.recent_transactions.map((txn) => (
                    <tr key={txn.id} className="border-t border-line">
                      <td className="py-3 text-muted">{when(txn.timestamp)}</td>
                      <td>
                        <div className="text-white">{txn.merchant}</div>
                        <div className="text-xs text-muted">{txn.category}</div>
                      </td>
                      <td>{txn.transaction_type}</td>
                      <td className="font-mono">{money(txn.amount)}</td>
                      <td>
                        <RiskBadge level={txn.risk_level} score={txn.risk_score} />
                      </td>
                      <td>
                        <StatusBadge status={txn.status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </article>
        <article className="rounded-xl border border-line bg-panel p-4 xl:col-span-2">
          <h2 className="mb-3 text-lg font-semibold">Attention queue</h2>
          {data.attention_queue.length === 0 ? (
            <EmptyState title="Queue is clear" body="Open and in-review alerts will collect here." />
          ) : (
            <div className="space-y-3">
              {data.attention_queue.map((alert) => (
                <div key={alert.id} className="rounded-lg border border-line bg-ink p-3">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-xs font-medium uppercase tracking-wide text-white">{alert.alert_type.replaceAll("_", " ")}</p>
                    <RiskBadge level={alert.risk_level} />
                  </div>
                  <p className="mt-2 text-sm text-muted">{alert.explanation}</p>
                  <div className="mt-3 flex items-center justify-between">
                    <span className="font-mono text-sm">
                      {money(alert.amount)} · {alert.risk_score}
                    </span>
                    <Button onClick={() => navigate(`/fraud-alerts?alert=${alert.id}`)}>Review</Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </article>
      </section>
    </div>
  );
}
