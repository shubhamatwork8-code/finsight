import { useEffect, useState, type ReactNode } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { analyticsApi } from "../api";
import { errorMessage } from "../api/client";
import { useMoney } from "../components/Currency";
import { ErrorState, LoadingState } from "../components/States";
import { Topbar } from "../components/Topbar";
import { shortDate } from "../lib/format";

const COLORS: Record<string, string> = { LOW: "#3ddc97", MEDIUM: "#f5b942", HIGH: "#ff6b6b", CREDIT: "#5b9dff", DEBIT: "#ff6b6b", TRANSFER: "#3ddc97" };

export function Analytics() {
  const money = useMoney();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [tx, setTx] = useState<Awaited<ReturnType<typeof analyticsApi.transactions>> | null>(null);
  const [risk, setRisk] = useState<Awaited<ReturnType<typeof analyticsApi.risk>> | null>(null);

  function load() {
    setLoading(true);
    Promise.all([analyticsApi.transactions(), analyticsApi.risk()])
      .then(([transactions, riskData]) => {
        setTx(transactions);
        setRisk(riskData);
        setError(null);
      })
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
  }, []);

  if (loading) return <LoadingState label="Loading analytics" />;
  if (error || !tx || !risk) return <ErrorState message={error || "Analytics unavailable"} onRetry={load} />;

  const volume = tx.volume_over_time.map((point) => ({ date: shortDate(point.date), amount: Number(point.amount) }));
  const types = tx.credit_vs_debit.map((point) => ({ type: point.type, amount: Number(point.amount) }));
  const categories = tx.category_breakdown.map((point) => ({ category: point.category, amount: Number(point.amount) }));
  const alerts = risk.alerts_over_time.map((point) => ({ date: shortDate(point.date), count: point.count }));
  const fraudCategories = risk.fraud_by_category.map((point) => ({ category: point.category, amount: Number(point.amount) }));
  const histogram = risk.score_histogram;
  const rules = risk.rule_frequency.map((point) => ({ rule: point.rule.replaceAll("_", " "), count: point.count }));
  const comparison = risk.model_comparison;

  return (
    <div>
      <Topbar eyebrow="Portfolio analytics" title="Analytics" subtitle="Charts read live aggregates from the API. Opening-balance postings are excluded." />
      <div className="grid gap-4 xl:grid-cols-2">
        <ChartCard title="Transaction volume over time">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={volume}>
              <CartesianGrid stroke="#243454" vertical={false} />
              <XAxis dataKey="date" stroke="#93a4c3" fontSize={12} />
              <YAxis stroke="#93a4c3" fontSize={12} />
              <Tooltip formatter={(value) => money(Number(value))} />
              <Bar dataKey="amount" name="Volume" fill="#5b9dff" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Credit vs debit">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={types}>
              <CartesianGrid stroke="#243454" vertical={false} />
              <XAxis dataKey="type" stroke="#93a4c3" fontSize={12} />
              <YAxis stroke="#93a4c3" fontSize={12} />
              <Tooltip formatter={(value) => money(Number(value))} />
              <Bar dataKey="amount" name="Amount">
                {types.map((entry) => (
                  <Cell key={entry.type} fill={COLORS[entry.type] || "#5b9dff"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Risk distribution">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={risk.risk_distribution} dataKey="count" nameKey="level" innerRadius={50} outerRadius={80}>
                {risk.risk_distribution.map((entry) => (
                  <Cell key={entry.level} fill={COLORS[entry.level]} />
                ))}
              </Pie>
              <Legend />
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Fraud alerts over time">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={alerts}>
              <CartesianGrid stroke="#243454" vertical={false} />
              <XAxis dataKey="date" stroke="#93a4c3" fontSize={12} />
              <YAxis allowDecimals={false} stroke="#93a4c3" fontSize={12} />
              <Tooltip />
              <Bar dataKey="count" name="Alerts" fill="#f5b942" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Fraud amount by category">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={fraudCategories}>
              <CartesianGrid stroke="#243454" vertical={false} />
              <XAxis dataKey="category" stroke="#93a4c3" fontSize={12} />
              <YAxis stroke="#93a4c3" fontSize={12} />
              <Tooltip formatter={(value) => money(Number(value))} />
              <Bar dataKey="amount" name="Flagged amount" fill="#ff6b6b" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Risk score distribution">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={histogram}>
              <CartesianGrid stroke="#243454" vertical={false} />
              <XAxis dataKey="bucket" stroke="#93a4c3" fontSize={12} />
              <YAxis allowDecimals={false} stroke="#93a4c3" fontSize={12} />
              <Tooltip />
              <Bar dataKey="count" name="Transactions" fill="#5b9dff" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Rule trigger frequency" className="xl:col-span-2">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={rules}>
              <CartesianGrid stroke="#243454" vertical={false} />
              <XAxis dataKey="rule" stroke="#93a4c3" fontSize={12} />
              <YAxis allowDecimals={false} stroke="#93a4c3" fontSize={12} />
              <Tooltip />
              <Bar dataKey="count" name="Triggers" fill="#f5b942" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Category breakdown" className="xl:col-span-2">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={categories} layout="vertical" margin={{ left: 32 }}>
              <CartesianGrid stroke="#243454" horizontal={false} />
              <XAxis type="number" stroke="#93a4c3" fontSize={12} />
              <YAxis type="category" dataKey="category" stroke="#93a4c3" fontSize={12} width={110} />
              <Tooltip formatter={(value) => money(Number(value))} />
              <Bar dataKey="amount" name="Amount" fill="#3ddc97" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
      <section className="mt-4 rounded-xl border border-line bg-panel p-4">
        <h2 className="text-lg font-semibold">Rule engine vs model</h2>
        <p className="mt-1 text-sm text-muted">{comparison.note}</p>
        <div className="table-wrap mt-3">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="text-xs uppercase text-muted">
              <tr>
                <th className="py-2">Approach</th>
                <th>Precision</th>
                <th>Recall</th>
                <th>F1</th>
                <th>PR-AUC</th>
                <th>False-positive rate</th>
              </tr>
            </thead>
            <tbody>
              {(
                [
                  ["Rules", comparison.rules],
                  ["Isolation Forest", comparison.model],
                  ["Hybrid", comparison.hybrid],
                ] as const
              ).map(([label, metrics]) => (
                <tr key={label} className="border-t border-line">
                  <td className="py-2">{label}</td>
                  <td className="font-mono">{metrics.precision}</td>
                  <td className="font-mono">{metrics.recall}</td>
                  <td className="font-mono">{metrics.f1}</td>
                  <td className="font-mono">{metrics.pr_auc}</td>
                  <td className="font-mono">{metrics.false_positive_rate}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function ChartCard({ title, children, className = "" }: { title: string; children: ReactNode; className?: string }) {
  return (
    <article className={`h-80 rounded-xl border border-line bg-panel p-4 ${className}`}>
      <h2 className="mb-2 text-lg font-semibold">{title}</h2>
      <div className="h-64">{children}</div>
    </article>
  );
}
