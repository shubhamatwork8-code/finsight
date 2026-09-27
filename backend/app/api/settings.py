from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.errors import AppError
from app.models import Account, LedgerEntry, Transaction
from app.schemas import RiskSettingsUpdate
from app.services.audit_service import write_audit
from app.services.fx_service import apply_conversion, fetch_rate
from app.services.presenters import present_settings
from app.services.tenancy import current_settings, owned_account_ids, visible_transactions
from app.utils.validators import LEDGER_CURRENCIES

router = APIRouter(prefix="/settings", tags=["settings"], dependencies=[Depends(get_current_user)])


def _validate(payload: RiskSettingsUpdate) -> None:
    if payload.unusual_start_hour >= payload.unusual_end_hour:
        raise AppError("INVALID_REQUEST", "Unusual-time window must start before it ends", 422)
    if payload.large_multiplier_medium >= payload.large_multiplier_high:
        raise AppError("INVALID_REQUEST", "The high-amount multiplier must be greater than the medium multiplier", 422)
    if payload.large_score_high < payload.large_score_medium:
        raise AppError("INVALID_REQUEST", "The high-amount score must be at least the medium score", 422)
    code = payload.ledger_currency.strip().upper()
    if code not in LEDGER_CURRENCIES:
        raise AppError("INVALID_REQUEST", "Choose a supported ledger currency", 422)
    payload.ledger_currency = code


@router.get("")
def get_settings(db: Session = Depends(get_db)):
    row = current_settings(db)
    return present_settings(row)


@router.patch("")
def patch_settings(payload: RiskSettingsUpdate, db: Session = Depends(get_db)):
    _validate(payload)
    row = current_settings(db)
    previous = (row.ledger_currency or "USD").upper()
    conversion = None
    if payload.ledger_currency != previous:
        rate = fetch_rate(previous, payload.ledger_currency)
        apply_conversion(db, rate, payload.ledger_currency)
        ids = owned_account_ids(db)
        if ids:
            db.query(Account).filter(Account.id.in_(ids)).update(
                {Account.currency: payload.ledger_currency}, synchronize_session=False
            )
            transaction_ids = [row.id for row in visible_transactions(db).all()]
            if transaction_ids:
                db.query(Transaction).filter(Transaction.id.in_(transaction_ids)).update(
                    {Transaction.currency: payload.ledger_currency}, synchronize_session=False
                )
        conversion = {
            "from": previous,
            "to": payload.ledger_currency,
            "rate": format(rate, "f"),
        }
        write_audit(
            db,
            action="CURRENCY_CHANGED",
            entity_type="settings",
            entity_id=row.id,
            message=f"Ledger converted from {previous} to {payload.ledger_currency} at {conversion['rate']}",
            details=conversion,
        )
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    body = present_settings(row)
    if conversion:
        body["conversion"] = conversion
    return body
