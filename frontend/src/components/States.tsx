export function LoadingState({ label = "Loading records" }: { label?: string }) {
  return (
    <div className="rounded-xl border border-line bg-panel px-4 py-10 text-center text-sm text-muted" role="status">
      {label}…
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="rounded-xl border border-coral/30 bg-coral/10 px-4 py-6 text-sm text-coral">
      <p>{message}</p>
      {onRetry ? (
        <button className="mt-3 underline" onClick={onRetry}>
          Try again
        </button>
      ) : null}
    </div>
  );
}

export function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-xl border border-dashed border-line px-4 py-10 text-center">
      <p className="text-sm font-medium text-white">{title}</p>
      <p className="mt-1 text-sm text-muted">{body}</p>
    </div>
  );
}

export function Pagination({
  page,
  pageSize,
  total,
  onPage,
}: {
  page: number;
  pageSize: number;
  total: number;
  onPage: (page: number) => void;
}) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  return (
    <div className="mt-4 flex items-center justify-between text-sm text-muted">
      <span>
        {total} records · page {page} of {pages}
      </span>
      <div className="flex gap-2">
        <button className="rounded-md border border-line px-3 py-1 disabled:opacity-40" disabled={page <= 1} onClick={() => onPage(page - 1)}>
          Previous
        </button>
        <button className="rounded-md border border-line px-3 py-1 disabled:opacity-40" disabled={page >= pages} onClick={() => onPage(page + 1)}>
          Next
        </button>
      </div>
    </div>
  );
}
