# Fraud detection

FinSight uses an explainable rule engine. It does not train or call a model. Thresholds live in `risk_settings` and can be changed from the Settings page. Changing them affects future evaluations only.

History for an account excludes the current transaction and `OPENING_BALANCE` postings.

## Rules

| Code | Default points | Trigger |
| --- | --- | --- |
| DUPLICATE_TRANSACTION | 40 | Same account, same merchant, same amount, within 5 minutes |
| LARGE_TRANSACTION | 35 if amount is at least 5x the account average, otherwise 25 if at least 3x | Requires at least 3 prior transactions. The comparison is the account average, not a global dollar cutoff |
| HIGH_FREQUENCY | 20 | 5 or more transactions for the account inside 5 minutes, including the current one |
| UNUSUAL_TIME | 10 | Hour is inside 00:00–05:00 and nighttime activity is not already normal for the account. This rule alone stays below the alert threshold |
| HISTORICAL_ANOMALY | 20 | Amount is more than 2 standard deviations above the mean, or the merchant is new and the amount is at least 2x the average |

The score is the sum of triggered points, capped at 100.

## Levels

- 0–29 LOW: stay `POSTED`, no alert
- 30–69 MEDIUM: `UNDER_REVIEW` and an open alert
- 70–100 HIGH: `UNDER_REVIEW` and an open alert

`alert_threshold` defaults to 30, which matches the medium band.

## Explanation

Each rule stores a code, the points, and a plain-language explanation. The transaction explanation joins those sentences and begins with "Transaction flagged for review because" when any rule fires.

The primary alert type is the triggered rule with the most points. Duplicate detection therefore outranks a large-amount rule when both fire, because 40 is higher than 35.

## Review

Alert statuses are `OPEN`, `UNDER_REVIEW`, `RESOLVED`, and `FALSE_POSITIVE`. Resolving an alert or marking it a false positive returns the transaction to `POSTED` and writes an audit row. The score on the transaction is kept so the original decision remains visible.

## What the demo is designed to show

- Two Gucci Boutique NY debits of $850.00 two minutes apart. The second is a high duplicate.
- An Apex Equipment debit that is far above Northwind Operating's recent average.
- A Night Kiosk debit at 02:14 that adds unusual-time points without opening an alert by itself.
- Five Rapid Parts debits inside four minutes on Vendor Clearing. The last one records high frequency.
