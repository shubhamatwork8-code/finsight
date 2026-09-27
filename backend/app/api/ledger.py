from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.errors import AppError
from app.core.money import money
from app.models import Account, LedgerEntry
from app.services.context import current_user_id
from app.services.presenters import account_names, decimal_text, present_ledger_entry
from app.services.tenancy import owned_account_ids, require_visible_transaction

router = APIRouter(prefix="/ledger", tags=["ledger"], dependencies=[Depends(get_current_user)])


def _filtered_query(
    db: Session,
    *,
    account_id: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
    include_system: bool,
):
    owned = owned_account_ids(db)
    query = db.query(LedgerEntry)
    if not owned:
        query = query.filter(LedgerEntry.id == "")
    else:
        query = query.filter(LedgerEntry.account_id.in_(owned))
    if account_id:
        if account_id not in owned:
            raise AppError("ACCOUNT_NOT_FOUND", "Account was not found", 404)
        query = query.filter(LedgerEntry.account_id == account_id)
    elif not include_system:
        system_ids = [
            row.id
            for row in db.query(Account.id).filter(
                Account.user_id == current_user_id.get(), Account.account_type == "SYSTEM"
            )
        ]
        if system_ids:
            query = query.filter(LedgerEntry.account_id.notin_(system_ids))
    if date_from:
        query = query.filter(LedgerEntry.created_at >= date_from)
    if date_to:
        query = query.filter(LedgerEntry.created_at <= date_to)
    return query


@router.get("")
def list_ledger(
    account_id: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    include_system: bool = True,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = _filtered_query(
        db,
        account_id=account_id,
        date_from=date_from,
        date_to=date_to,
        include_system=include_system,
    )
    rows_all = query.order_by(LedgerEntry.created_at.desc(), LedgerEntry.id.desc()).all()
    debit_total = money(sum((row.amount for row in rows_all if row.entry_type == "DEBIT"), 0))
    credit_total = money(sum((row.amount for row in rows_all if row.entry_type == "CREDIT"), 0))
    total = len(rows_all)
    start = (page - 1) * page_size
    rows = rows_all[start : start + page_size]
    names = account_names(db)
    return {
        "items": [present_ledger_entry(row, names) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "debit_total": decimal_text(debit_total or 0),
        "credit_total": decimal_text(credit_total or 0),
        "settlement_account_id": next(
            (
                row.id
                for row in db.query(Account.id).filter(
                    Account.user_id == current_user_id.get(), Account.account_type == "SYSTEM"
                )
            ),
            None,
        ),
    }


@router.get("/{transaction_id}")
def ledger_for_transaction(transaction_id: str, db: Session = Depends(get_db)):
    require_visible_transaction(db, transaction_id)
    rows = (
        db.query(LedgerEntry)
        .filter(LedgerEntry.transaction_id == transaction_id)
        .order_by(LedgerEntry.id.asc())
        .all()
    )
    names = account_names(db)
    debit_total = money(sum((row.amount for row in rows if row.entry_type == "DEBIT"), 0))
    credit_total = money(sum((row.amount for row in rows if row.entry_type == "CREDIT"), 0))
    return {
        "transaction_id": transaction_id,
        "items": [present_ledger_entry(row, names) for row in rows],
        "debit_total": decimal_text(debit_total),
        "credit_total": decimal_text(credit_total),
    }
