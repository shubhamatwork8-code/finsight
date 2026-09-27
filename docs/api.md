# API

Base path: `/api`

Errors use a consistent JSON body:

```json
{"error": "INSUFFICIENT_BALANCE", "message": "Transaction cannot be completed because the account balance is insufficient"}
```

Validation errors use `INVALID_REQUEST` and HTTP 422. Missing accounts use `ACCOUNT_NOT_FOUND` and HTTP 404. Database failures use `DATABASE_ERROR` and HTTP 500 without a stack trace.

## Accounts

- `GET /api/accounts`
- `POST /api/accounts`
- `GET /api/accounts/{id}`
- `GET /api/accounts/{id}/transactions`

## Transactions

- `GET /api/transactions` supports `search`, `transaction_type`, `risk_level`, `account_id`, `status`, `sort`, `direction`, `page`, `page_size`
- `POST /api/transactions`
- `GET /api/transactions/{id}` includes ledger lines and the risk explanation
- `POST /api/transactions/import` multipart file field `file`

## Ledger

- `GET /api/ledger` supports `account_id`, `date_from`, `date_to`, `include_system`, `page`, `page_size`
- `GET /api/ledger/{transaction_id}`

The list response includes `debit_total` and `credit_total` for the current filter.

## Fraud

- `GET /api/fraud-alerts`
- `GET /api/fraud-alerts/{id}`
- `PATCH /api/fraud-alerts/{id}`
- `POST /api/fraud-alerts/{id}/review`

## Analytics and dashboard

- `GET /api/analytics/overview`
- `GET /api/analytics/transactions`
- `GET /api/analytics/risk`
- `GET /api/dashboard/summary`

## Audit, settings, health

- `GET /api/audit-logs`
- `GET /api/settings`
- `PATCH /api/settings`
- `GET /api/health`

There is no endpoint that edits or deletes audit rows.
