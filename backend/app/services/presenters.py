from decimal import Decimal

from app.core.money import money
from app.models import Account, AlertReview, FraudAlert, LedgerEntry, Transaction, User
from app.services.context import current_user_id
from app.services.fraud_service import rule_summary


def decimal_text(value) -> str:
    return format(money(value or Decimal("0")), "f")


def account_names(db) -> dict[str, str]:
    return {
        account.id: account.name
        for account in db.query(Account).filter(Account.user_id == current_user_id.get()).all()
    }


def present_account(db, account: Account) -> dict:
    count = (
        db.query(Transaction)
        .filter((Transaction.account_id == account.id) | (Transaction.destination_account_id == account.id))
        .count()
    )
    return {
        "id": account.id,
        "user_id": account.user_id,
        "name": account.name,
        "account_type": account.account_type,
        "balance": decimal_text(account.balance),
        "currency": account.currency,
        "status": account.status,
        "created_at": account.created_at.isoformat(timespec="seconds"),
        "transaction_count": count,
    }


def present_ledger_entry(entry: LedgerEntry, names: dict[str, str]) -> dict:
    return {
        "id": entry.id,
        "transaction_id": entry.transaction_id,
        "account_id": entry.account_id,
        "account_name": names.get(entry.account_id, entry.account_id),
        "entry_type": entry.entry_type,
        "amount": decimal_text(entry.amount),
        "currency": entry.currency,
        "created_at": entry.created_at.isoformat(timespec="seconds"),
    }


def present_transaction(db, transaction: Transaction, names: dict[str, str] | None = None, *, include_ledger: bool = False) -> dict:
    names = names or account_names(db)
    alert = (
        db.query(FraudAlert)
        .filter(FraudAlert.transaction_id == transaction.id)
        .order_by(FraudAlert.created_at.desc())
        .first()
    )
    payload = {
        "id": transaction.id,
        "account_id": transaction.account_id,
        "account_name": names.get(transaction.account_id, transaction.account_id),
        "destination_account_id": transaction.destination_account_id,
        "destination_account_name": names.get(transaction.destination_account_id) if transaction.destination_account_id else None,
        "transaction_type": transaction.transaction_type,
        "amount": decimal_text(transaction.amount),
        "currency": transaction.currency,
        "merchant": transaction.merchant,
        "category": transaction.category,
        "description": transaction.description,
        "timestamp": transaction.occurred_at.isoformat(timespec="seconds"),
        "location": transaction.location,
        "status": transaction.status,
        "risk_score": transaction.risk_score,
        "rule_score": _stored_rule_score(transaction),
        "ml_score": transaction.ml_score or 0,
        "rule_summary": rule_summary(transaction.triggered_rules or []),
        "risk_level": transaction.risk_level,
        "risk_explanation": transaction.risk_explanation,
        "triggered_rules": transaction.triggered_rules or [],
        "created_at": transaction.created_at.isoformat(timespec="seconds"),
        "alert_id": alert.id if alert else None,
    }
    if include_ledger:
        entries = (
            db.query(LedgerEntry)
            .filter(LedgerEntry.transaction_id == transaction.id)
            .order_by(LedgerEntry.id.asc())
            .all()
        )
        payload["ledger_entries"] = [present_ledger_entry(entry, names) for entry in entries]
    return payload


def present_alert(db, alert: FraudAlert, names: dict[str, str] | None = None) -> dict:
    names = names or account_names(db)
    transaction = db.get(Transaction, alert.transaction_id)
    return {
        "id": alert.id,
        "transaction_id": alert.transaction_id,
        "account_id": alert.account_id,
        "account_name": names.get(alert.account_id, alert.account_id),
        "alert_type": alert.alert_type,
        "risk_score": alert.risk_score,
        "risk_level": alert.risk_level,
        "explanation": alert.explanation,
        "triggered_rules": alert.triggered_rules or [],
        "status": alert.status,
        "resolution_note": alert.resolution_note,
        "created_at": alert.created_at.isoformat(timespec="seconds"),
        "updated_at": alert.updated_at.isoformat(timespec="seconds"),
        "amount": decimal_text(transaction.amount) if transaction else None,
        "currency": transaction.currency if transaction else None,
        "merchant": transaction.merchant if transaction else None,
        "rule_score": _stored_rule_score(transaction) if transaction else None,
        "ml_score": transaction.ml_score if transaction else None,
        "rule_summary": rule_summary(alert.triggered_rules or []),
        "reviews": _reviews(db, alert.id),
    }


def _stored_rule_score(transaction: Transaction) -> int:
    rule_score = transaction.rule_score or 0
    model_score = transaction.ml_score or 0
    if rule_score == 0 and model_score == 0 and transaction.triggered_rules:
        return transaction.risk_score or 0
    return rule_score


def _reviews(db, alert_id: str) -> list[dict]:
    rows = db.query(AlertReview).filter(AlertReview.alert_id == alert_id).order_by(AlertReview.created_at.asc()).all()
    names = {user.id: user.full_name for user in db.query(User).filter(User.id.in_([row.user_id for row in rows] or [""])).all()}
    return [
        {
            "id": row.id,
            "user_id": row.user_id,
            "reviewer_name": names.get(row.user_id, row.user_id),
            "from_status": row.from_status,
            "to_status": row.to_status,
            "note": row.note,
            "created_at": row.created_at.isoformat(timespec="seconds"),
        }
        for row in rows
    ]


def present_settings(row) -> dict:
    return {
        "duplicate_window_minutes": row.duplicate_window_minutes,
        "duplicate_score": row.duplicate_score,
        "frequency_threshold": row.frequency_threshold,
        "frequency_window_minutes": row.frequency_window_minutes,
        "frequency_score": row.frequency_score,
        "large_multiplier_medium": row.large_multiplier_medium,
        "large_multiplier_high": row.large_multiplier_high,
        "large_score_medium": row.large_score_medium,
        "large_score_high": row.large_score_high,
        "unusual_time_score": row.unusual_time_score,
        "unusual_start_hour": row.unusual_start_hour,
        "unusual_end_hour": row.unusual_end_hour,
        "anomaly_score": row.anomaly_score,
        "min_history_count": row.min_history_count,
        "alert_threshold": row.alert_threshold,
        "ledger_currency": getattr(row, "ledger_currency", None) or "USD",
    }
