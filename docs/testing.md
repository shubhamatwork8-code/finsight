# Testing

Run from `backend`:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

The suite uses in-memory SQLite and bootstraps the demo user, settlement account, and default risk settings. It does not seed the narrative demo, so the cases stay small and deterministic.

Covered behavior:

- Account creation and opening-balance ledger credit
- Credit, debit, and a 2,000 transfer from 10,000 / 5,000 to 8,000 / 7,000
- Ledger debit total equals credit total
- Sum of all balances, including settlement, stays at zero
- Insufficient balance does not leave a transaction or extra ledger rows
- Large-amount detection against account history
- Duplicate detection
- Frequency detection
- Score cap at 100
- Alert resolution returns the transaction to posted
- CSV import keeps one valid row and rejects an invalid amount and a missing account
- API validation and missing-account errors

The transfer case is the financial consistency check: source debit, destination credit, and both balances must agree with the ledger lines.
