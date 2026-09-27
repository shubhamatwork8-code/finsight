from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import Account, RiskSettings, Transaction
from app.services.bootstrap import DEMO_USER_ID, SETTINGS_ID
from app.services.context import current_user_id


def owned_customer_ids(db: Session) -> list[str]:
    user_id = current_user_id.get()
    return [
        row.id
        for row in db.query(Account.id).filter(Account.user_id == user_id, Account.account_type != "SYSTEM").all()
    ]


def owned_account_ids(db: Session) -> list[str]:
    user_id = current_user_id.get()
    return [row.id for row in db.query(Account.id).filter(Account.user_id == user_id).all()]


def visible_transactions(db: Session):
    ids = owned_customer_ids(db)
    query = db.query(Transaction)
    if not ids:
        return query.filter(Transaction.id == "")
    return query.filter(or_(Transaction.account_id.in_(ids), Transaction.destination_account_id.in_(ids)))


def require_customer_account(db: Session, account_id: str) -> Account:
    account = db.get(Account, account_id)
    if account is None or account.account_type == "SYSTEM" or account.user_id != current_user_id.get():
        raise AppError("ACCOUNT_NOT_FOUND", "Account was not found", 404)
    return account


def current_settings(db: Session) -> RiskSettings:
    user_id = current_user_id.get()
    row = db.query(RiskSettings).filter(RiskSettings.user_id == user_id).one_or_none()
    if row is None and user_id == DEMO_USER_ID:
        row = db.get(RiskSettings, SETTINGS_ID)
    if row is None:
        raise AppError("SETTINGS_NOT_FOUND", "Risk settings were not found", 404)
    return row


def require_visible_transaction(db: Session, transaction_id: str) -> Transaction:
    transaction = db.get(Transaction, transaction_id)
    ids = set(owned_customer_ids(db))
    if transaction is None or (transaction.account_id not in ids and transaction.destination_account_id not in ids):
        raise AppError("TRANSACTION_NOT_FOUND", "Transaction was not found", 404)
    return transaction
