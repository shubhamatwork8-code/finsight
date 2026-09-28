import { FormEvent, useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { accountsApi } from "../api";
import { errorMessage } from "../api/client";
import { useLedgerCurrency, useMoney } from "../components/Currency";
import { StatusBadge } from "../components/KpiCard";
import { Field, Modal, controlClass } from "../components/Modal";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { Button, Topbar } from "../components/Topbar";
import { when } from "../lib/format";
import type { Account } from "../types";

export function Accounts() {
  const money = useMoney();
  const { code } = useLedgerCurrency();
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const open = params.get("create") === "1";

  function load() {
    setLoading(true);
    accountsApi
      .list()
      .then((rows) => {
        setAccounts(rows);
        setError(null);
      })
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
  }, []);

  async function onCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setSaving(true);
    setFormError(null);
    try {
      await accountsApi.create({
        name: String(form.get("name") || ""),
        account_number: String(form.get("account_number") || ""),
        ifsc_code: String(form.get("ifsc_code") || ""),
        account_type: String(form.get("account_type") || "CHECKING"),
        currency: code,
        opening_balance: String(form.get("opening_balance") || "0"),
      });
      setParams({});
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
        eyebrow="Customer accounts"
        title="Accounts"
        subtitle="Balances are derived from ledger postings. Opening balances are posted as system credits."
        actions={<Button tone="primary" onClick={() => setParams({ create: "1" })}>New Account</Button>}
      />
      {loading ? <LoadingState label="Loading accounts" /> : null}
      {error ? <ErrorState message={error} onRetry={load} /> : null}
      {!loading && !error && accounts.length === 0 ? (
        <EmptyState title="No accounts yet" body="Create a checking, savings, or operations account to begin posting." />
      ) : null}
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {accounts.map((account) => (
          <button
            key={account.id}
            onClick={() => navigate(`/accounts/${account.id}`)}
            className="rounded-xl border border-line bg-panel p-4 text-left shadow-card hover:border-signal"
          >
            <div className="flex items-start justify-between">
              <div>
                <p className="font-mono text-xs text-muted">{account.id}</p>
                <h2 className="mt-1 text-lg font-semibold">{account.name}</h2>
              </div>
              <StatusBadge status={account.status} />
            </div>
            <p className="mt-5 font-mono text-2xl">{money(account.balance)}</p>
            <p className="mt-2 text-sm text-muted">
              {account.account_type} · {account.transaction_count} transactions · opened {when(account.created_at)}
            </p>
          </button>
        ))}
      </div>
      {open ? (
        <Modal title="New account" onClose={() => setParams({})}>
          <form className="grid gap-3" onSubmit={onCreate}>
            <Field label="Account name">
              <input name="name" required className={controlClass} />
            </Field>
            <Field label="Account number">
              <input name="account_number" required className={controlClass} />
            </Field>
            <Field label="IFSC Code">
              <input name="ifsc_code" required className={controlClass} />
            </Field>
            <Field label="Account type">
              <select name="account_type" className={controlClass} defaultValue="CHECKING">
                <option>CHECKING</option>
                <option>SAVINGS</option>
                <option>OPERATIONS</option>
              </select>
            </Field>
            <Field label="Opening balance">
              <input name="opening_balance" type="number" min="0" step="0.01" defaultValue="0" className={controlClass} />
            </Field>
            <p className="text-sm text-muted">This account uses the ledger currency, {code}. Change that in Settings.</p>
            {formError ? <p className="text-sm text-coral">{formError}</p> : null}
            <Button type="submit" tone="primary" disabled={saving}>
              {saving ? "Creating…" : "Create account"}
            </Button>
          </form>
        </Modal>
      ) : null}
    </div>
  );
}
