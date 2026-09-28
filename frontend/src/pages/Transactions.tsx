import { FormEvent, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { accountsApi, ledgerApi, transactionsApi } from "../api";
import { errorMessage } from "../api/client";
import { useLedgerCurrency, useMoney } from "../components/Currency";
import { RiskBadge, StatusBadge } from "../components/KpiCard";
import { Field, Modal, controlClass } from "../components/Modal";
import { EmptyState, ErrorState, LoadingState, Pagination } from "../components/States";
import { Button, Topbar } from "../components/Topbar";
import { when } from "../lib/format";
import type { Account, ImportSummary, LedgerPage, Transaction } from "../types";

export function Transactions() {
  const money = useMoney();
  const { code } = useLedgerCurrency();
  const [params, setParams] = useSearchParams();
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [rows, setRows] = useState<Transaction[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [type, setType] = useState("");
  const [risk, setRisk] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [detail, setDetail] = useState<Transaction | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [importSummary, setImportSummary] = useState<ImportSummary | null>(null);
  const [ledger, setLedger] = useState<LedgerPage | null>(null);
  const [view, setView] = useState<"transactions" | "ledger">("transactions");
  const record = params.get("record") === "1";
  const importing = params.get("import") === "1";
  const [idempotencyKey, setIdempotencyKey] = useState("");

  function load(nextPage = page) {
    setLoading(true);
    const query: Record<string, string | number> = { page: nextPage, page_size: 8, sort: "timestamp", direction: "desc" };
    if (search.trim()) query.search = search.trim();
    if (type) query.transaction_type = type;
    if (risk) query.risk_level = risk;
    Promise.all([transactionsApi.list(query), accountsApi.list(), ledgerApi.list({ page: 1, page_size: 12, include_system: "true" })])
      .then(([txnPage, accountRows, ledgerPage]) => {
        setRows(txnPage.items);
        setTotal(txnPage.total);
        setAccounts(accountRows);
        setLedger(ledgerPage);
        setError(null);
      })
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [type, risk]);

  useEffect(() => {
    if (record) setIdempotencyKey(crypto.randomUUID());
  }, [record]);

  async function openDetail(id: string) {
    const txn = await transactionsApi.get(id);
    setDetail(txn);
  }

  async function onRecord(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setSaving(true);
    setFormError(null);
    try {
      const txType = String(form.get("transaction_type"));
      await transactionsApi.create({
        account_id: form.get("account_id"),
        destination_account_id: txType === "TRANSFER" ? form.get("destination_account_id") : null,
        transaction_type: txType,
        amount: form.get("amount"),
        currency: code,
        merchant: form.get("merchant"),
        category: form.get("category"),
        description: form.get("description") || "",
        timestamp: new Date().toISOString(),
        location: null,
      }, idempotencyKey);
      setParams({});
      load(1);
    } catch (err) {
      setFormError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  }


  async function onImport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const file = (event.currentTarget.elements.namedItem("file") as HTMLInputElement).files?.[0];
    if (!file) return;
    setSaving(true);
    setFormError(null);
    try {
      const summary = await transactionsApi.importCsv(file);
      setImportSummary(summary);
      load(1);
    } catch (err) {
      setFormError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <Topbar
        eyebrow="Postings"
        title="Transactions"
        subtitle="Every posting validates accounts, writes a balanced ledger, updates balances, and runs the risk engine."
        actions={
          <>
            <Button onClick={() => setParams({ import: "1" })}>Import CSV</Button>
            <Button tone="primary" onClick={() => setParams({ record: "1" })}>
              Record Transaction
            </Button>
          </>
        }
      />
      <div className="mb-4 flex flex-wrap gap-2">
        <Button tone={view === "transactions" ? "primary" : "secondary"} onClick={() => setView("transactions")}>
          Transactions
        </Button>
        <Button tone={view === "ledger" ? "primary" : "secondary"} onClick={() => setView("ledger")}>
          Ledger
        </Button>
      </div>
      {view === "transactions" ? (
        <>
          <div className="mb-4 grid gap-2 md:grid-cols-4">
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search merchant, id, category"
              className={controlClass}
              aria-label="Search transactions"
            />
            <select value={type} onChange={(event) => setType(event.target.value)} className={controlClass} aria-label="Filter by type">
              <option value="">All types</option>
              <option>CREDIT</option>
              <option>DEBIT</option>
              <option>TRANSFER</option>
            </select>
            <select value={risk} onChange={(event) => setRisk(event.target.value)} className={controlClass} aria-label="Filter by risk">
              <option value="">All risk levels</option>
              <option>LOW</option>
              <option>MEDIUM</option>
              <option>HIGH</option>
            </select>
            <Button
              onClick={() => {
                setPage(1);
                load(1);
              }}
            >
              Apply search
            </Button>
          </div>
          {loading ? <LoadingState label="Loading transactions" /> : null}
          {error ? <ErrorState message={error} onRetry={() => load(page)} /> : null}
          {!loading && !error && rows.length === 0 ? (
            <EmptyState title="No matching transactions" body="Adjust the filters or record a new posting." />
          ) : null}
          {!loading && rows.length > 0 ? (
            <div className="table-wrap rounded-xl border border-line bg-panel">
              <table className="w-full min-w-[860px] text-left text-sm">
                <thead className="text-xs uppercase text-muted">
                  <tr>
                    <th className="px-3 py-3">Timestamp</th>
                    <th>Account</th>
                    <th>Merchant</th>
                    <th>Type</th>
                    <th>Amount</th>
                    <th>Risk</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((txn) => (
                    <tr key={txn.id} className="cursor-pointer border-t border-line hover:bg-panel2" onClick={() => openDetail(txn.id)}>
                      <td className="px-3 py-3 text-muted">{when(txn.timestamp)}</td>
                      <td>{txn.account_name}</td>
                      <td>
                        <div>{txn.merchant}</div>
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
          ) : null}
          <Pagination
            page={page}
            pageSize={8}
            total={total}
            onPage={(next) => {
              setPage(next);
              load(next);
            }}
          />
        </>
      ) : (
        <section className="rounded-xl border border-line bg-panel p-4">
          <div className="mb-3 flex flex-wrap gap-6 text-sm">
            <span>Debit total <strong className="font-mono">{money(ledger?.debit_total)}</strong></span>
            <span>Credit total <strong className="font-mono">{money(ledger?.credit_total)}</strong></span>
          </div>
          <p className="mb-3 text-sm text-muted">
            External credits and debits include an offsetting settlement entry so the books stay balanced. Transfers move value between customer accounts.
          </p>
          {!ledger || ledger.items.length === 0 ? (
            <EmptyState title="Ledger is empty" body="Entries appear when a transaction posts." />
          ) : (
            <div className="table-wrap">
              <table className="w-full min-w-[720px] text-left text-sm">
                <thead className="text-xs uppercase text-muted">
                  <tr>
                    <th className="py-2">Entry</th>
                    <th>Transaction</th>
                    <th>Account</th>
                    <th>Direction</th>
                    <th>Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {ledger.items.map((entry) => (
                    <tr key={entry.id} className="border-t border-line">
                      <td className="py-2 font-mono text-xs">{entry.id}</td>
                      <td className="font-mono text-xs">{entry.transaction_id}</td>
                      <td>{entry.account_name}</td>
                      <td className={entry.entry_type === "DEBIT" ? "text-coral" : "text-emerald"}>{entry.entry_type}</td>
                      <td className="font-mono">{money(entry.amount)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}
      {detail ? (
        <Modal title={detail.id} onClose={() => setDetail(null)}>
          <p className="font-mono text-2xl">{money(detail.amount)}</p>
          <p className="mt-1 text-sm text-muted">
            {detail.merchant} · {detail.category} · {detail.transaction_type}
          </p>
          <div className="mt-3 flex gap-2">
            <RiskBadge level={detail.risk_level} score={detail.risk_score} />
            <StatusBadge status={detail.status} />
          </div>
          <p className="mt-4 text-sm leading-6">{detail.rule_summary || detail.risk_explanation}</p>
          <p className="mt-2 text-sm text-muted">
            Hybrid {detail.risk_score} · Rules {detail.rule_score} · Model {detail.ml_score}
          </p>
          <p className="mt-2 text-sm leading-6">{detail.risk_explanation}</p>
          {detail.triggered_rules.length > 0 ? (
            <ul className="mt-3 space-y-2 text-sm">
              {detail.triggered_rules.map((rule) => (
                <li key={rule.code} className="rounded-md border border-line px-3 py-2">
                  <span className="font-medium">{rule.code.replaceAll("_", " ")}</span>
                  <span className="ml-2 font-mono text-muted">+{rule.points}</span>
                  <p className="text-muted">{rule.explanation}</p>
                </li>
              ))}
            </ul>
          ) : null}
          <h3 className="mb-2 mt-5 text-sm font-semibold uppercase tracking-wide text-muted">Ledger entries</h3>
          <div className="space-y-2">
            {(detail.ledger_entries || []).map((entry) => (
              <div key={entry.id} className="flex justify-between rounded-md bg-ink px-3 py-2 text-sm">
                <span>
                  {entry.account_name} · {entry.entry_type}
                </span>
                <span className="font-mono">{money(entry.amount)}</span>
              </div>
            ))}
          </div>
        </Modal>
      ) : null}
      {record ? (
        <Modal title="Record transaction" onClose={() => setParams({})}>
          <form className="grid gap-3 md:grid-cols-2" onSubmit={onRecord}>
            <Field label="Type">
              <select name="transaction_type" className={controlClass} defaultValue="DEBIT">
                <option>DEBIT</option>
                <option>CREDIT</option>
                <option>TRANSFER</option>
              </select>
            </Field>
            <Field label="Amount">
              <input name="amount" required type="number" min="0.01" step="0.01" className={controlClass} />
            </Field>
            <Field label="Account">
              <select name="account_id" required className={controlClass}>
                {accounts.map((account) => (
                  <option key={account.id} value={account.id}>
                    {account.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Destination (transfers)">
              <select name="destination_account_id" className={controlClass}>
                <option value="">None</option>
                {accounts.map((account) => (
                  <option key={account.id} value={account.id}>
                    {account.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Merchant">
              <input name="merchant" required className={controlClass} />
            </Field>
            <Field label="Category">
              <input name="category" required className={controlClass} />
            </Field>
            <div className="md:col-span-2">
              <Field label="Description">
                <input name="description" className={controlClass} />
              </Field>
            </div>
            {formError ? <p className="text-sm text-coral md:col-span-2">{formError}</p> : null}
            <Button type="submit" tone="primary" disabled={saving}>
              {saving ? "Posting…" : "Post transaction"}
            </Button>
          </form>
        </Modal>
      ) : null}

      {importing ? (
        <Modal
          title="Import CSV"
          onClose={() => {
            setImportSummary(null);
            setParams({});
          }}
        >
          <p className="mb-3 text-sm text-muted">
            Required columns: account_id, transaction_type, amount, currency, merchant, category, description, timestamp, location, destination_account_id.
            Invalid rows are rejected and reported.
          </p>
          <form className="grid gap-3" onSubmit={onImport}>
            <input name="file" type="file" accept=".csv,text/csv" required className="text-sm" aria-label="CSV file" />
            {formError ? <p className="text-sm text-coral">{formError}</p> : null}
            <Button type="submit" tone="primary" disabled={saving}>
              {saving ? "Importing…" : "Import valid rows"}
            </Button>
          </form>
          {importSummary ? (
            <div className="mt-4 rounded-md border border-line p-3 text-sm">
              <p>Imported: {importSummary.imported}</p>
              <p>Rejected: {importSummary.rejected}</p>
              {importSummary.errors.map((item) => (
                <p key={item.row} className="text-coral">
                  Row {item.row}: {item.message}
                </p>
              ))}
            </div>
          ) : null}
        </Modal>
      ) : null}
    </div>
  );
}
