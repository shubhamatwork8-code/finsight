import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { accountsApi, ledgerApi } from "../api";
import { errorMessage } from "../api/client";
import { useMoney } from "../components/Currency";
import { StatusBadge } from "../components/KpiCard";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { Topbar } from "../components/Topbar";
import { when } from "../lib/format";
import type { Account, LedgerEntry, Transaction } from "../types";

export function AccountDetail() {
  const { id = "" } = useParams();
  const money = useMoney();
  const [account, setAccount] = useState<Account | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [entries, setEntries] = useState<LedgerEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    Promise.all([
      accountsApi.get(id),
      accountsApi.transactions(id),
      ledgerApi.list({ account_id: id, page: 1, page_size: 50, include_system: false }),
    ])
      .then(([row, history, ledger]) => {
        if (!active) return;
        setAccount(row);
        setTransactions(history);
        setEntries(ledger.items);
        setError(null);
      })
      .catch((err) => {
        if (active) setError(errorMessage(err));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [id]);

  return (
    <div>
      <Topbar
        eyebrow="Customer account"
        title={account?.name ?? "Account"}
        subtitle={account ? `${account.id} · ${account.account_type} · ${account.currency}` : "Ledger-backed balance and posting history."}
        actions={
          <Link to="/accounts" className="rounded-md border border-line px-3 py-2 text-sm text-white">
            All accounts
          </Link>
        }
      />
      {loading ? <LoadingState label="Loading account" /> : null}
      {error ? <ErrorState message={error} /> : null}
      {account ? (
        <>
          <section className="grid gap-3 md:grid-cols-4">
            <article className="rounded-xl border border-line bg-panel p-4">
              <p className="text-xs uppercase text-muted">Balance</p>
              <p className="mt-2 font-mono text-2xl">{money(account.balance)}</p>
            </article>
            <article className="rounded-xl border border-line bg-panel p-4">
              <p className="text-xs uppercase text-muted">Status</p>
              <div className="mt-3">
                <StatusBadge status={account.status} />
              </div>
            </article>
            <article className="rounded-xl border border-line bg-panel p-4">
              <p className="text-xs uppercase text-muted">Opened</p>
              <p className="mt-2 text-sm">{when(account.created_at)}</p>
            </article>
            <article className="rounded-xl border border-line bg-panel p-4">
              <p className="text-xs uppercase text-muted">Transactions</p>
              <p className="mt-2 font-mono text-2xl">{account.transaction_count}</p>
            </article>
          </section>
          <section className="mt-6">
            <h2 className="text-lg font-semibold">Transactions</h2>
            {transactions.length === 0 ? (
              <EmptyState title="No transactions" body="This account has no posted activity." />
            ) : (
              <div className="table-wrap mt-3">
                <table className="w-full min-w-[720px] text-left text-sm">
                  <thead className="text-xs uppercase text-muted">
                    <tr>
                      <th className="py-2">When</th>
                      <th>Merchant</th>
                      <th>Type</th>
                      <th>Amount</th>
                      <th>Risk</th>
                    </tr>
                  </thead>
                  <tbody>
                    {transactions.map((txn) => (
                      <tr key={txn.id} className="border-t border-line">
                        <td className="py-2 text-muted">{when(txn.timestamp)}</td>
                        <td>{txn.merchant}</td>
                        <td>{txn.transaction_type}</td>
                        <td className="font-mono">{money(txn.amount)}</td>
                        <td>
                          {txn.risk_level} {txn.risk_score}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
          <section className="mt-6">
            <h2 className="text-lg font-semibold">Ledger lines</h2>
            {entries.length === 0 ? (
              <EmptyState title="No ledger lines" body="Postings for this account will appear here." />
            ) : (
              <div className="table-wrap mt-3">
                <table className="w-full min-w-[640px] text-left text-sm">
                  <thead className="text-xs uppercase text-muted">
                    <tr>
                      <th className="py-2">Entry</th>
                      <th>Transaction</th>
                      <th>Side</th>
                      <th>Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    {entries.map((entry) => (
                      <tr key={entry.id} className="border-t border-line">
                        <td className="py-2 font-mono text-xs">{entry.id}</td>
                        <td className="font-mono text-xs">{entry.transaction_id}</td>
                        <td>{entry.entry_type}</td>
                        <td className="font-mono">{money(entry.amount)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      ) : null}
    </div>
  );
}
