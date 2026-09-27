from fastapi import APIRouter, Depends, File, Header, Query, UploadFile
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.errors import AppError
from app.models import Transaction
from app.schemas import ReceiptConfirm, TransactionCreate
from app.services.audit_service import write_audit
from app.services.csv_service import import_csv_text
from app.services.presenters import account_names, present_transaction
from app.services.receipt_service import extract_receipt
from app.services.tenancy import current_settings, require_visible_transaction, visible_transactions
from app.services.transaction_service import TransactionInput, create_transaction

router = APIRouter(prefix="/transactions", tags=["transactions"], dependencies=[Depends(get_current_user)])

SORTS = {
    "timestamp": Transaction.occurred_at,
    "amount": Transaction.amount,
    "risk_score": Transaction.risk_score,
    "merchant": Transaction.merchant,
}


@router.get("")
def list_transactions(
    search: str | None = None,
    transaction_type: str | None = None,
    risk_level: str | None = None,
    account_id: str | None = None,
    status: str | None = None,
    sort: str = "timestamp",
    direction: str = "desc",
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = visible_transactions(db)
    if search:
        term = f"%{search.strip().lower()}%"
        query = query.filter(
            or_(
                func.lower(Transaction.merchant).like(term),
                func.lower(Transaction.id).like(term),
                func.lower(Transaction.category).like(term),
                func.lower(Transaction.description).like(term),
            )
        )
    if transaction_type:
        query = query.filter(Transaction.transaction_type == transaction_type.upper())
    if risk_level:
        query = query.filter(Transaction.risk_level == risk_level.upper())
    if account_id:
        query = query.filter(
            (Transaction.account_id == account_id) | (Transaction.destination_account_id == account_id)
        )
    if status:
        query = query.filter(Transaction.status == status.upper())
    total = query.count()
    column = SORTS.get(sort, Transaction.occurred_at)
    ordering = column.asc() if direction == "asc" else column.desc()
    rows = query.order_by(ordering, Transaction.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    names = account_names(db)
    return {
        "items": [present_transaction(db, row, names) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("", status_code=201)
def post_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    transaction = create_transaction(
        db,
        TransactionInput(
            account_id=payload.account_id,
            destination_account_id=payload.destination_account_id,
            transaction_type=payload.transaction_type,
            amount=payload.amount,
            currency=payload.currency,
            merchant=payload.merchant,
            category=payload.category,
            description=payload.description,
            timestamp=payload.timestamp,
            location=payload.location,
        ),
        idempotency_key=idempotency_key,
    )
    return present_transaction(db, transaction, include_ledger=True)


@router.post("/import")
async def import_transactions(file: UploadFile = File(...), db: Session = Depends(get_db)):
    raw = await file.read()
    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise AppError("INVALID_CSV", "CSV file must be UTF-8 encoded") from exc
    return import_csv_text(db, content)


@router.post("/receipts")
async def read_receipt(file: UploadFile = File(...), db: Session = Depends(get_db)):
    data = await file.read()
    settings = current_settings(db)
    return extract_receipt(file.filename or "receipt", data, settings.ledger_currency or "USD")


@router.post("/receipts/confirm", status_code=201)
def confirm_receipt(
    payload: ReceiptConfirm,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    def _audit(transaction):
        write_audit(
            db,
            action="RECEIPT_IMPORTED",
            entity_type="transaction",
            entity_id=transaction.id,
            message=f"Transaction {transaction.id} posted from a receipt",
            details={"filename": (payload.source_filename or "")[:180]},
        )

    transaction = create_transaction(
        db,
        TransactionInput(
            account_id=payload.account_id,
            transaction_type=payload.transaction_type,
            amount=payload.amount,
            currency=payload.currency,
            merchant=payload.merchant,
            category=payload.category or "Uncategorized",
            description=payload.description,
            timestamp=payload.timestamp,
            location=payload.location,
        ),
        idempotency_key=idempotency_key,
        before_commit=_audit,
    )
    return present_transaction(db, transaction, include_ledger=True)


@router.get("/{transaction_id}")
def get_transaction(transaction_id: str, db: Session = Depends(get_db)):
    transaction = require_visible_transaction(db, transaction_id)
    return present_transaction(db, transaction, include_ledger=True)
