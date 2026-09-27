import { useEffect, useState } from "react";
import { auditApi } from "../api";
import { errorMessage } from "../api/client";
import { EmptyState, ErrorState, LoadingState, Pagination } from "../components/States";
import { Topbar } from "../components/Topbar";
import { when } from "../lib/format";
import type { AuditEvent } from "../types";

export function AuditLog() {
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [rows, setRows] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function load(next = page) {
    setLoading(true);
    auditApi
      .list(next)
      .then((payload) => {
        setRows(payload.items);
        setTotal(payload.total);
        setError(null);
      })
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div>
      <Topbar
        eyebrow="Immutable activity"
        title="Audit Log"
        subtitle="Account, ledger, fraud, and review events are appended here. The log cannot be edited from this screen."
      />
      {loading ? <LoadingState label="Loading audit log" /> : null}
      {error ? <ErrorState message={error} onRetry={() => load(page)} /> : null}
      {!loading && !error && rows.length === 0 ? <EmptyState title="No audit events" body="Events appear as soon as accounts and transactions are posted." /> : null}
      <ol className="space-y-2">
        {rows.map((event) => (
          <li key={event.id} className="grid grid-cols-[140px_1fr] gap-3 rounded-lg border border-line bg-panel px-4 py-3 text-sm">
            <time className="font-mono text-xs text-muted">{when(event.created_at)}</time>
            <div>
              <p>{event.message}</p>
              <p className="text-xs text-muted">
                {event.action} · {event.entity_type} {event.entity_id}
              </p>
            </div>
          </li>
        ))}
      </ol>
      <Pagination
        page={page}
        pageSize={30}
        total={total}
        onPage={(next) => {
          setPage(next);
          load(next);
        }}
      />
    </div>
  );
}
