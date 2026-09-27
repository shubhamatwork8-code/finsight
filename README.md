# FinSight — Enterprise Risk Engine

FinSight is a focused FinTech portfolio application for transaction monitoring, double-entry ledger accounting, and explainable fraud detection. It is an academic project, not a bank. Customer balances, ledger rows, risk scores, and alerts all come from the same backend workflow.

## Problem statement

Operations teams need to see whether a posting is financially valid and why it looks risky. A balance field that changes by itself cannot explain a transfer, and a label that only says "fraud" cannot be reviewed. FinSight posts each transaction through validation, a balanced ledger, a balance update, a rule-based risk score, an alert when the score warrants review, and an audit trail.

## Key features

- Dashboard with live balances, volume, risk mix, recent postings, and an attention queue
- Accounts with opening balances posted through the ledger
- Credits, debits, and transfers with validation and insufficient-balance protection
- Double-entry ledger, including an external settlement account so customer cash movements stay balanced
- Explainable rule scores plus an Isolation Forest anomaly score, combined into a hybrid score
- Benchmark comparison of precision, recall, F1, PR-AUC, and false-positive rate
- Fraud alert review, resolution, and false-positive marking
- Analytics from backend aggregates
- Append-only audit log
- CSV import that accepts valid rows and reports rejected rows
- Receipt import from a PDF or photo, reviewed before it is posted
- Deterministic demo data

Out of scope: cryptocurrency, trading, loans, payments gateways, chat, KYC, card management, and real bank integrations.

## Architecture

```text
Auth → Accounts → Transactions → Ledger → Fraud Engine → Alerts → Analyst Review
```

Sign-in issues a signed JWT. Passwords are hashed with Argon2id. Each posting writes a balanced debit and credit, scores the rules and an Isolation Forest model, and keeps a hybrid score. A repeated request with the same idempotency key returns the original transaction. Ledger lines are appended; a currency change adds a reversal and a restated pair instead of editing old lines.

```text
React + TypeScript
        │  REST / Axios, JWT bearer token
        ▼
FastAPI
        │
        ├── Accounts
        ├── Transactions
        ├── Ledger
        └── Fraud engine (rules + Isolation Forest + hybrid score)
                │
                ▼
        Alerts → analyst review
                │
                ▼
        SQLite by default, PostgreSQL when DATABASE_URL points at Postgres
```

The database is the source of truth. The frontend does not calculate balances or risk scores.

## Technology stack

- Frontend: React, TypeScript, Vite, Tailwind CSS, React Router, Recharts, Lucide, Axios
- Backend: Python, FastAPI, SQLAlchemy, Pydantic
- Database: SQLite for a zero-dependency local run; PostgreSQL via `DATABASE_URL` and `docker-compose.yml`
- Tests: Pytest and FastAPI's test client

Docker is not required to run the project. This machine did not have Docker or a local PostgreSQL server, so the default database is a SQLite file using the same SQLAlchemy models, `Decimal` money columns, and transactional commit/rollback behavior. Point `DATABASE_URL` at PostgreSQL when you want row locks and `NUMERIC` in Postgres.

## Database schema

| Table | Role |
| --- | --- |
| users | One login per person, plus the shared demo |
| accounts | Customer accounts plus the external settlement account |
| transactions | Business posting, status, and risk result |
| ledger_entries | Debit and credit lines |
| fraud_alerts | Review records for scores at or above the threshold |
| audit_logs | Append-only operational history |
| risk_settings | Configurable rule thresholds |

Monetary amounts use `Numeric(14, 2)` and Python `Decimal`. See `docs/database-schema.md`.

## Fraud detection methodology

The engine is rule-based. It does not use a machine-learning model. Every non-system transaction is scored from the account's own history:

- Duplicate merchant and amount inside a time window
- Amount that is several times the account average
- Too many transactions in a short window
- A small score for unusual hours
- A historical anomaly for a new merchant or a statistical outlier

Details and point values are in `docs/fraud-detection.md`.

## Risk scoring methodology

Scores are additive and capped at 100.

- 0–29: LOW, transaction stays posted, no alert
- 30–69: MEDIUM, status becomes under review, alert opens
- 70–100: HIGH, same review path with a high-risk label

The API returns the rules, the points, and a sentence that starts with "Transaction flagged for review because...".

## API documentation

Interactive docs are at `http://127.0.0.1:8000/docs` after the backend starts. The route list is in `docs/api.md`.

## Installation

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
cd ..\frontend
npm install
```

## Environment variables

Copy `backend/.env.example` to `backend/.env` if you want to override the defaults.

- `DATABASE_URL` — default `sqlite:///./data/finsight.db`
- `SEED_ON_STARTUP` — default `true`. Leave it on for the first start so the classroom demo books load, then set it to `false` if you do not want startup to look for an empty ledger again.
- `CORS_ORIGINS` — comma-separated browser origins that may call the API
- `SECRET_KEY` — signs session tokens. Replace the development default before any shared deployment.
- `DEMO_PASSWORD` — password for `demo@finsight.local`. Applied only when that user has no password yet. Default `FinSight-demo-1`.
- `VITE_API_URL` — frontend build-time API origin, for example `https://api.example.edu`. Leave it empty for the Vite dev proxy.

PostgreSQL example:

```text
DATABASE_URL=postgresql+psycopg://finsight:finsight@localhost:5432/finsight
```

From the repository root, `docker compose up -d` starts Postgres when Docker is installed.

## Database setup

SQLite creates `backend/data/finsight.db` on startup and seeds demo data when the customer account table is empty.

For PostgreSQL, create the database, set `DATABASE_URL`, and start the API. Tables are created on startup. Demo data loads when no customer accounts exist.

## Running the backend

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

## Running the frontend

```powershell
cd frontend
npm run dev
```

Open `http://127.0.0.1:5173`. The Vite dev server proxies `/api` to the backend.

People sign in at `/login`. The demo login is `demo@finsight.local` / `FinSight-demo-1` and already contains the fraud story. A new registration starts with an empty ledger that no other login can read. Currency conversion and risk thresholds apply only to the signed-in user.

## Deploying for a class

Use PostgreSQL, a private `SECRET_KEY`, and the public origin of the frontend.

```text
DATABASE_URL=postgresql+psycopg://finsight:finsight@db:5432/finsight
SECRET_KEY=replace-with-a-long-random-string
CORS_ORIGINS=https://finsight.example.edu
SEED_ON_STARTUP=true
DEMO_PASSWORD=FinSight-demo-1
```

Build the frontend with the API origin:

```powershell
cd frontend
$env:VITE_API_URL="https://api.example.edu"
npm run build
```

Serve `frontend/dist` as a static site and run the API with uvicorn behind HTTPS. After the demo seed has loaded once, set `SEED_ON_STARTUP=false`. People register themselves. There is no shared password and no extra admin role. Receipt photos are read on the server with the OCR library in `requirements.txt`; the image is not stored after the draft is returned.

`docker compose up -d` from the repository root starts PostgreSQL when Docker is available. The API process is still started separately.

## Running tests

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

Tests use an in-memory SQLite database and do not touch the demo file.

## Demo data

Startup seed creates three customer accounts (Northwind Operating, Harbor Payroll Reserve, Vendor Clearing), an external settlement account, ordinary spend, a duplicate Gucci Boutique NY charge, a large Apex Equipment invoice, a nighttime purchase, and a same-hour vendor burst. Alerts, ledger lines, and balances are produced by the services, not inserted as disconnected rows.

A sample import file is at `backend/sample_data/transactions.csv`. It uses account ids `ACC-1001` and `ACC-1003`, which match a fresh seed.

## Example transaction flow

1. Validate the amount, timestamp, currency, and accounts.
2. Refuse the posting if a debit or transfer would overdraw the source.
3. Insert the transaction.
4. Insert balanced ledger lines and update balances.
5. Score the source account against its history.
6. Open an alert when the score reaches the threshold.
7. Append audit events.
8. Commit. A failure rolls the posting back.

## Screenshots

Capture the dashboard, alert review, and ledger after the first local run and place images in `docs/screenshots/`. The repository does not ship placeholder screenshots.

## Future improvements

- Run the admission demo on PostgreSQL in every environment
- Calibrate unusual-hour behavior with a longer history
- Add Alembic migrations once the schema needs versioned changes

Do not describe those items as implemented.
