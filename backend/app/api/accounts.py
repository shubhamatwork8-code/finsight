from fastapi import APIRouter, Depends
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import Account, Transaction
from app.schemas import AccountCreate
from app.services.context import current_user_id
from app.services.presenters import account_names, present_account, present_transaction
from app.services.tenancy import require_customer_account
from app.services.transaction_service import create_account

router = APIRouter(prefix="/accounts", tags=["accounts"], dependencies=[Depends(get_current_user)])


@router.get("")
def list_accounts(
    search: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Account).filter(
        Account.account_type != "SYSTEM",
        Account.user_id == current_user_id.get(),
    )
    if status:
        query = query.filter(Account.status == status.upper())
    if search:
        term = f"%{search.strip().lower()}%"
        query = query.filter(or_(func.lower(Account.name).like(term), func.lower(Account.id).like(term)))
    accounts = query.order_by(Account.created_at.asc()).all()
    return [present_account(db, account) for account in accounts]


@router.post("", status_code=201)
def post_account(payload: AccountCreate, db: Session = Depends(get_db)):
    account = create_account(
        db,
        name=payload.name,
        account_number=payload.account_number,
        ifsc_code=payload.ifsc_code,
        account_type=payload.account_type,
        currency=payload.currency,
        opening_balance=payload.opening_balance,
    )
    return present_account(db, account)


@router.get("/{account_id}")
def get_account(account_id: str, db: Session = Depends(get_db)):
    account = require_customer_account(db, account_id)
    return present_account(db, account)


@router.get("/{account_id}/transactions")
def account_transactions(account_id: str, db: Session = Depends(get_db)):
    require_customer_account(db, account_id)
    rows = (
        db.query(Transaction)
        .filter((Transaction.account_id == account_id) | (Transaction.destination_account_id == account_id))
        .order_by(Transaction.occurred_at.desc())
        .all()
    )
    names = account_names(db)
    return [present_transaction(db, row, names) for row in rows]
