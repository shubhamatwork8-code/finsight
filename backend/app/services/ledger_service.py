from decimal import Decimal

from app.core.errors import AppError
from app.core.money import money
from app.models import Account, LedgerEntry
from app.utils.ids import next_public_id


def _apply_balance(account: Account, entry_type: str, amount: Decimal) -> None:
    amount = money(amount)
    if entry_type == "CREDIT":
        account.balance = money(account.balance + amount)
        return
    if account.account_type != "SYSTEM" and money(account.balance) < amount:
        raise AppError(
            "INSUFFICIENT_BALANCE",
            "Transaction cannot be completed because the account balance is insufficient",
        )
    account.balance = money(account.balance - amount)


def _settlement_for(db, user_id: str) -> Account:
    return db.query(Account).filter(Account.user_id == user_id, Account.account_type == "SYSTEM").one()


def post_entry(
    db,
    *,
    transaction_id: str,
    account: Account,
    entry_type: str,
    amount: Decimal,
    currency: str,
    generation: int = 0,
    entry_kind: str = "ORIGINAL",
) -> LedgerEntry:
    _apply_balance(account, entry_type, amount)
    entry = LedgerEntry(
        id=next_public_id(db, LedgerEntry.id, "LED"),
        transaction_id=transaction_id,
        account_id=account.id,
        entry_type=entry_type,
        amount=money(amount),
        currency=currency,
        generation=generation,
        entry_kind=entry_kind,
    )
    db.add(entry)
    db.flush()
    return entry


def append_entry(
    db,
    *,
    transaction_id: str,
    account_id: str,
    entry_type: str,
    amount: Decimal,
    currency: str,
    generation: int,
    entry_kind: str,
) -> LedgerEntry:
    entry = LedgerEntry(
        id=next_public_id(db, LedgerEntry.id, "LED"),
        transaction_id=transaction_id,
        account_id=account_id,
        entry_type=entry_type,
        amount=money(amount),
        currency=currency,
        generation=generation,
        entry_kind=entry_kind,
    )
    db.add(entry)
    db.flush()
    return entry


def assert_balanced(entries: list[LedgerEntry]) -> None:
    debit = money(sum((entry.amount for entry in entries if entry.entry_type == "DEBIT"), Decimal("0")))
    credit = money(sum((entry.amount for entry in entries if entry.entry_type == "CREDIT"), Decimal("0")))
    if debit != credit:
        raise AppError("UNBALANCED_ENTRY", "The journal entry is not balanced and was rejected.")


def post_balanced_entries(db, *, transaction, source: Account, destination: Account | None) -> list[LedgerEntry]:
    amount = money(transaction.amount)
    currency = transaction.currency
    entries: list[LedgerEntry] = []
    if transaction.transaction_type == "CREDIT":
        settlement = _settlement_for(db, source.user_id)
        entries.append(post_entry(db, transaction_id=transaction.id, account=source, entry_type="CREDIT", amount=amount, currency=currency))
        entries.append(post_entry(db, transaction_id=transaction.id, account=settlement, entry_type="DEBIT", amount=amount, currency=currency))
    elif transaction.transaction_type == "DEBIT":
        settlement = _settlement_for(db, source.user_id)
        entries.append(post_entry(db, transaction_id=transaction.id, account=source, entry_type="DEBIT", amount=amount, currency=currency))
        entries.append(post_entry(db, transaction_id=transaction.id, account=settlement, entry_type="CREDIT", amount=amount, currency=currency))
    elif transaction.transaction_type == "TRANSFER":
        if destination is None:
            raise AppError("INVALID_TRANSACTION", "Transfer requires a destination account")
        entries.append(post_entry(db, transaction_id=transaction.id, account=source, entry_type="DEBIT", amount=amount, currency=currency))
        entries.append(post_entry(db, transaction_id=transaction.id, account=destination, entry_type="CREDIT", amount=amount, currency=currency))
    else:
        raise AppError("INVALID_TRANSACTION", "Unsupported transaction type")
    assert_balanced(entries)
    return entries
