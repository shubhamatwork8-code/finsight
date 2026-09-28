from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.money import money
from app.core.timeutil import utcnow
from app.models import Account, AlertReview, FraudAlert, IdempotencyRecord, Transaction
from app.services.audit_service import write_audit
from app.services.bootstrap import OPENING_BALANCE_CATEGORY
from app.services.context import current_user_id
from app.services.fraud_service import TxView, evaluate_risk, primary_rule, risk_level, rule_summary
from app.services.ledger_service import post_balanced_entries
from app.services.ml_service import anomaly_score
from app.services.tenancy import current_settings
from app.utils.ids import next_public_id
from app.utils.validators import require_currency, require_positive_amount


class TransactionInput:
    def __init__(
        self,
        *,
        account_id: str,
        transaction_type: str,
        amount: Decimal,
        currency: str,
        merchant: str,
        category: str,
        description: str,
        timestamp: datetime,
        location: str | None,
        destination_account_id: str | None = None,
    ):
        self.account_id = account_id
        self.transaction_type = transaction_type
        self.amount = amount
        self.currency = currency
        self.merchant = merchant
        self.category = category
        self.description = description
        self.timestamp = timestamp
        self.location = location
        self.destination_account_id = destination_account_id


def _lock_account(db: Session, account_id: str) -> Account:
    query = db.query(Account).filter(Account.id == account_id)
    bind = db.get_bind()
    if bind is not None and bind.dialect.name == "postgresql":
        query = query.with_for_update()
    account = query.one_or_none()
    if account is None:
        raise AppError("ACCOUNT_NOT_FOUND", f"Account {account_id} was not found", 404)
    return account


def _require_active_customer(account: Account, *, allow_system: bool = False) -> None:
    if account.account_type == "SYSTEM" and not allow_system:
        raise AppError("ACCOUNT_NOT_FOUND", f"Account {account.id} was not found", 404)
    if account.status != "ACTIVE":
        raise AppError("ACCOUNT_INACTIVE", f"Account {account.name} is not active")


def create_account(
    db: Session,
    *,
    name: str,
    account_number: str = "0000000000",
    ifsc_code: str = "DEFAULT000",
    account_type: str,
    currency: str,
    opening_balance: Decimal = Decimal("0"),
) -> Account:
    try:
        cleaned_name = name.strip()
        if not cleaned_name:
            raise AppError("INVALID_REQUEST", "Account name is required", 422)
        if account_type not in {"CHECKING", "SAVINGS", "OPERATIONS"}:
            raise AppError("INVALID_REQUEST", "Account type is not supported", 422)
        code = require_currency(currency)
        ledger = current_settings(db)
        expected = ledger.ledger_currency if ledger.ledger_currency else "USD"
        if code != expected:
            raise AppError(
                "CURRENCY_MISMATCH",
                f"New accounts must use the ledger currency {expected}. Change it in Settings.",
                422,
            )
        opening = money(opening_balance)
        if opening < 0:
            raise AppError("INVALID_REQUEST", "Opening balance cannot be negative", 422)
        account = Account(
            id=next_public_id(db, Account.id, "ACC"),
            user_id=current_user_id.get(),
            name=cleaned_name,
            account_number=account_number,
            ifsc_code=ifsc_code,
            account_type=account_type,
            currency=code,
            balance=Decimal("0.00"),
            status="ACTIVE",
        )
        db.add(account)
        db.flush()
        write_audit(
            db,
            action="ACCOUNT_CREATED",
            entity_type="account",
            entity_id=account.id,
            message=f"Account {account.id} created",
        )
        if opening > 0:
            _create_transaction(
                db,
                TransactionInput(
                    account_id=account.id,
                    transaction_type="CREDIT",
                    amount=opening,
                    currency=code,
                    merchant="Opening Balance",
                    category=OPENING_BALANCE_CATEGORY,
                    description="Opening balance",
                    timestamp=utcnow(),
                    location=None,
                ),
                skip_fraud=True,
            )
        db.commit()
        db.refresh(account)
        return account
    except Exception:
        db.rollback()
        raise


def create_transaction(
    db: Session,
    payload: TransactionInput,
    *,
    skip_fraud: bool = False,
    idempotency_key: str | None = None,
    before_commit=None,
) -> Transaction:
    key = (idempotency_key or "").strip()[:80]
    try:
        if key:
            existing = _idempotent_transaction(db, key)
            if existing is not None:
                return existing
        transaction = _create_transaction(db, payload, skip_fraud=skip_fraud)
        if key:
            db.add(
                IdempotencyRecord(
                    id=next_public_id(db, IdempotencyRecord.id, "IDM"),
                    user_id=current_user_id.get(),
                    idempotency_key=key,
                    transaction_id=transaction.id,
                )
            )
        if before_commit is not None:
            before_commit(transaction)
        db.commit()
        db.refresh(transaction)
        return transaction
    except Exception:
        db.rollback()
        if key:
            existing = _idempotent_transaction(db, key)
            if existing is not None:
                return existing
        raise


def _create_transaction(db: Session, payload: TransactionInput, *, skip_fraud: bool) -> Transaction:
    tx_type = payload.transaction_type.strip().upper()
    if tx_type not in {"CREDIT", "DEBIT", "TRANSFER"}:
        raise AppError("INVALID_TRANSACTION", "Transaction type must be CREDIT, DEBIT, or TRANSFER")
    if payload.timestamp is None:
        raise AppError("INVALID_TRANSACTION", "Transaction must have a valid timestamp")
    amount = require_positive_amount(payload.amount)
    merchant = (payload.merchant or "").strip()
    category = (payload.category or "").strip()
    if not merchant or not category:
        raise AppError("INVALID_TRANSACTION", "Merchant and category are required")

    ids = [payload.account_id]
    if tx_type == "TRANSFER":
        if not payload.destination_account_id:
            raise AppError("INVALID_TRANSACTION", "Transfer must have a destination account")
        if payload.destination_account_id == payload.account_id:
            raise AppError("INVALID_TRANSACTION", "Transfer source and destination must be different accounts")
        ids.append(payload.destination_account_id)
    locked = {account_id: _lock_account(db, account_id) for account_id in sorted(set(ids))}
    source = locked[payload.account_id]
    _require_active_customer(source)
    if source.user_id != current_user_id.get():
        raise AppError("ACCOUNT_NOT_FOUND", f"Account {source.id} was not found", 404)
    destination = None
    if tx_type == "TRANSFER":
        destination = locked[payload.destination_account_id]
        _require_active_customer(destination)
        if destination.user_id != source.user_id:
            raise AppError("INVALID_TRANSACTION", "Transfer accounts must belong to the same login")
        if destination.currency != source.currency:
            raise AppError("INVALID_TRANSACTION", "Transfer accounts must use the same currency")

    currency = require_currency(payload.currency or source.currency)
    if currency != source.currency:
        raise AppError("INVALID_TRANSACTION", "Transaction currency must match the account currency")

    if tx_type in {"DEBIT", "TRANSFER"} and money(source.balance) < amount:
        raise AppError(
            "INSUFFICIENT_BALANCE",
            "Transaction cannot be completed because the account balance is insufficient",
        )

    transaction = Transaction(
        id=next_public_id(db, Transaction.id, "TX"),
        account_id=source.id,
        destination_account_id=destination.id if destination else None,
        transaction_type=tx_type,
        amount=amount,
        currency=currency,
        merchant=merchant,
        category=category,
        description=(payload.description or "").strip(),
        occurred_at=payload.timestamp,
        location=(payload.location or "").strip() or None,
        status="POSTED",
        risk_score=0,
        risk_level="LOW",
        risk_explanation="",
        triggered_rules=[],
    )
    db.add(transaction)
    db.flush()
    post_balanced_entries(db, transaction=transaction, source=source, destination=destination)
    write_audit(
        db,
        action="TRANSACTION_CREATED",
        entity_type="transaction",
        entity_id=transaction.id,
        message=f"Transaction {transaction.id} created",
    )
    write_audit(
        db,
        action="LEDGER_UPDATED",
        entity_type="transaction",
        entity_id=transaction.id,
        message="Ledger updated",
    )

    if skip_fraud or category == OPENING_BALANCE_CATEGORY:
        transaction.risk_explanation = "Risk evaluation skipped for system posting."
        return transaction

    settings = current_settings(db)
    prior_rows = (
        db.query(Transaction)
        .filter(Transaction.account_id == source.id, Transaction.id != transaction.id)
        .all()
    )
    prior = [
        TxView(
            id=row.id,
            amount=row.amount,
            merchant=row.merchant,
            category=row.category,
            occurred_at=row.occurred_at,
        )
        for row in prior_rows
    ]
    current = TxView(
        id=transaction.id,
        amount=transaction.amount,
        merchant=transaction.merchant,
        category=transaction.category,
        occurred_at=transaction.occurred_at,
    )
    result = evaluate_risk(current, prior, settings, currency=source.currency)
    model_score = anomaly_score(current, prior, result.score)
    hybrid = min(100, int(round((0.7 * result.score) + (0.3 * model_score))))
    transaction.rule_score = result.score
    transaction.ml_score = model_score
    transaction.risk_score = hybrid
    transaction.risk_level = risk_level(hybrid)
    transaction.risk_explanation = result.explanation
    transaction.triggered_rules = result.rules_payload
    transaction.status = "POSTED" if transaction.risk_level == "LOW" else "UNDER_REVIEW"
    write_audit(
        db,
        action="FRAUD_EVALUATED",
        entity_type="transaction",
        entity_id=transaction.id,
        message="Fraud analysis completed",
        details={
            "rule_score": result.score,
            "ml_score": model_score,
            "risk_score": hybrid,
            "risk_level": transaction.risk_level,
            "rules": rule_summary(result.rules_payload),
        },
    )
    write_audit(
        db,
        action="RISK_SCORED",
        entity_type="transaction",
        entity_id=transaction.id,
        message=f"Risk score = {hybrid}",
    )
    if hybrid >= int(settings.alert_threshold):
        alert = FraudAlert(
            id=next_public_id(db, FraudAlert.id, "ALR"),
            transaction_id=transaction.id,
            account_id=source.id,
            alert_type=primary_rule(result),
            risk_score=hybrid,
            risk_level=transaction.risk_level,
            explanation=result.explanation,
            triggered_rules=result.rules_payload,
            status="OPEN",
            resolution_note="",
        )
        db.add(alert)
        db.flush()
        label = "High-risk alert generated" if result.level == "HIGH" else "Fraud alert generated"
        write_audit(
            db,
            action="ALERT_GENERATED",
            entity_type="fraud_alert",
            entity_id=alert.id,
            message=label,
            details={"transaction_id": transaction.id, "risk_score": result.score},
        )
    return transaction


def review_alert(db: Session, alert_id: str, *, status: str, resolution_note: str) -> FraudAlert:
    try:
        alert = db.get(FraudAlert, alert_id)
        account = db.get(Account, alert.account_id) if alert is not None else None
        if alert is None or account is None or account.user_id != current_user_id.get():
            raise AppError("ALERT_NOT_FOUND", f"Alert {alert_id} was not found", 404)
        if status not in {"OPEN", "UNDER_REVIEW", "RESOLVED", "FALSE_POSITIVE"}:
            raise AppError("INVALID_REQUEST", "Alert status is not supported", 422)
        previous = alert.status
        note = (resolution_note or "").strip()
        alert.status = status
        alert.resolution_note = note
        reviewer = current_user_id.get()
        db.add(
            AlertReview(
                id=next_public_id(db, AlertReview.id, "REV"),
                alert_id=alert.id,
                user_id=reviewer,
                from_status=previous,
                to_status=status,
                note=note,
            )
        )
        transaction = db.get(Transaction, alert.transaction_id)
        if transaction is not None and status in {"RESOLVED", "FALSE_POSITIVE"}:
            transaction.status = "POSTED"
        if status == "UNDER_REVIEW":
            message = "Alert marked as reviewed"
            action = "ALERT_REVIEWED"
        elif status == "RESOLVED":
            message = "Alert marked resolved"
            action = "ALERT_RESOLVED"
        elif status == "FALSE_POSITIVE":
            message = "Alert marked false positive"
            action = "ALERT_RESOLVED"
        else:
            message = "Alert reopened"
            action = "ALERT_REVIEWED"
        write_audit(
            db,
            action=action,
            entity_type="fraud_alert",
            entity_id=alert.id,
            message=message,
            details={"status": status, "from_status": previous, "note": note, "reviewer_id": reviewer},
        )
        db.commit()
        db.refresh(alert)
        return alert
    except Exception:
        db.rollback()
        raise


def _idempotent_transaction(db: Session, key: str) -> Transaction | None:
    row = (
        db.query(IdempotencyRecord)
        .filter(IdempotencyRecord.user_id == current_user_id.get(), IdempotencyRecord.idempotency_key == key)
        .one_or_none()
    )
    if row is None:
        return None
    return db.get(Transaction, row.transaction_id)
