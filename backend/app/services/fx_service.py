import json
from decimal import Decimal
from urllib.error import URLError
from urllib.request import urlopen

from app.core.errors import AppError
from app.core.money import money
from app.models import Account, LedgerEntry
from app.services.ledger_service import append_entry
from app.services.tenancy import owned_account_ids, visible_transactions


def fetch_rate(source: str, target: str) -> Decimal:
    if source == target:
        return Decimal("1")
    for getter in (_frankfurter_rate, _open_rate):
        try:
            return getter(source, target)
        except Exception:
            continue
    raise AppError("FX_UNAVAILABLE", f"No exchange rate is available from {source} to {target}.")


def _frankfurter_rate(source: str, target: str) -> Decimal:
    url = f"https://api.frankfurter.app/latest?from={source}&to={target}"
    try:
        with urlopen(url, timeout=10) as response:
            payload = json.load(response)
        raw = payload["rates"][target]
    except (URLError, TimeoutError, KeyError, ValueError, json.JSONDecodeError) as exc:
        raise AppError("FX_UNAVAILABLE", f"No exchange rate is available from {source} to {target}.") from exc
    return _positive_rate(raw, source, target)


def _open_rate(source: str, target: str) -> Decimal:
    url = f"https://open.er-api.com/v6/latest/{source}"
    try:
        with urlopen(url, timeout=10) as response:
            payload = json.load(response)
        raw = payload["rates"][target]
    except (URLError, TimeoutError, KeyError, ValueError, json.JSONDecodeError) as exc:
        raise AppError("FX_UNAVAILABLE", f"No exchange rate is available from {source} to {target}.") from exc
    return _positive_rate(raw, source, target)


def _positive_rate(raw, source: str, target: str) -> Decimal:
    rate = Decimal(str(raw))
    if rate <= 0:
        raise AppError("FX_UNAVAILABLE", f"No exchange rate is available from {source} to {target}.")
    return rate


def apply_conversion(db, rate: Decimal, target_currency: str) -> None:
    factor = Decimal(str(rate))
    if factor <= 0:
        raise AppError("FX_UNAVAILABLE", "The exchange rate must be positive.")
    account_ids = owned_account_ids(db)
    if not account_ids:
        return
    for transaction in visible_transactions(db).all():
        entries = db.query(LedgerEntry).filter(LedgerEntry.transaction_id == transaction.id).all()
        active = _active_entries(entries)
        if not active:
            continue
        generation = max((entry.generation or 0) for entry in entries) + 1
        for entry in active:
            opposite = "CREDIT" if entry.entry_type == "DEBIT" else "DEBIT"
            append_entry(
                db,
                transaction_id=transaction.id,
                account_id=entry.account_id,
                entry_type=opposite,
                amount=entry.amount,
                currency=entry.currency,
                generation=generation,
                entry_kind="REVERSAL",
            )
            append_entry(
                db,
                transaction_id=transaction.id,
                account_id=entry.account_id,
                entry_type=entry.entry_type,
                amount=money(Decimal(entry.amount) * factor),
                currency=target_currency,
                generation=generation,
                entry_kind="RESTATED",
            )
        transaction.amount = money(Decimal(transaction.amount) * factor)
        transaction.currency = target_currency
    for account in db.query(Account).filter(Account.id.in_(account_ids)).all():
        posted = db.query(LedgerEntry).filter(LedgerEntry.account_id == account.id).all()
        balance = Decimal("0.00")
        for entry in posted:
            if entry.entry_type == "CREDIT":
                balance += entry.amount
            else:
                balance -= entry.amount
        account.balance = money(balance)
    db.flush()


def _active_entries(entries: list[LedgerEntry]) -> list[LedgerEntry]:
    if not entries:
        return []
    latest = max((entry.generation or 0) for entry in entries)
    return [
        entry
        for entry in entries
        if (entry.generation or 0) == latest and (entry.entry_kind or "ORIGINAL") != "REVERSAL"
    ]
