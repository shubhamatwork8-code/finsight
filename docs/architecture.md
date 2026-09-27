# Architecture

FinSight is a single backend service and a single-page frontend.

```mermaid
flowchart TD
  UI[React UI] --> API[FastAPI]
  API --> TX[Transaction service]
  TX --> VAL[Validation]
  VAL --> LED[Ledger service]
  LED --> DB[(SQLite or PostgreSQL)]
  TX --> RISK[Rule-based risk engine]
  RISK --> ALERT[Fraud alerts]
  TX --> AUD[Audit log]
  ALERT --> DB
  AUD --> DB
  API --> ANA[Analytics queries]
  ANA --> DB
```

The frontend calls Axios services under `frontend/src/api`. Pages render loading, empty, and error states. They do not hardcode dashboard totals.

A financial operation commits only after validation, ledger lines, balance updates, risk evaluation, optional alert creation, and audit rows succeed. `create_transaction` rolls the session back on any exception.

PostgreSQL takes row locks with `SELECT ... FOR UPDATE` while locking account ids in sorted order. SQLite relies on the database transaction around the same sequence.

## Transaction processing

```mermaid
flowchart TD
  A[Transaction request] --> B[Validate amount, accounts, currency, timestamp]
  B --> C{Sufficient balance?}
  C -->|No| R[Rollback and return INSUFFICIENT_BALANCE]
  C -->|Yes| D[Insert transaction]
  D --> E[Insert balanced ledger entries]
  E --> F[Update balances]
  F --> G[Evaluate fraud rules]
  G --> H{Score >= threshold?}
  H -->|Yes| I[Open fraud alert]
  H -->|No| J[Leave posted]
  I --> K[Write audit log]
  J --> K
  K --> L[Commit]
```

## Fraud detection

```mermaid
flowchart TD
  T[Posted transaction] --> H[Load prior account history]
  H --> D{Duplicate?}
  H --> L{Large versus this account?}
  H --> F{High frequency?}
  H --> U{Unusual hour?}
  H --> A{Historical anomaly?}
  D --> S[Sum points and cap at 100]
  L --> S
  F --> S
  U --> S
  A --> S
  S --> LV{0-29 / 30-69 / 70-100}
  LV --> OUT[Score, level, rules, explanation]
```

## Repository layout

```text
backend/app
  api/            HTTP routes
  core/           config, database, money type, errors
  models/         SQLAlchemy models
  schemas/        request models
  services/       ledger, transactions, fraud, analytics, csv, audit
  seed.py         demo data through the services
frontend/src
  api/            Axios clients
  components/     layout, badges, states, modal
  pages/          dashboard, accounts, transactions, alerts, analytics, audit, settings
docs/             architecture, schema, fraud, API, tests
```
