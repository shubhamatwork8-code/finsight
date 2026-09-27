from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.errors import AppError
from app.models import FraudAlert
from app.schemas import AlertReview, AlertUpdate
from app.services.presenters import account_names, present_alert
from app.services.transaction_service import review_alert

from app.services.tenancy import owned_customer_ids

router = APIRouter(prefix="/fraud-alerts", tags=["fraud"], dependencies=[Depends(get_current_user)])


@router.get("")
def list_alerts(
    status: str | None = None,
    risk_level: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    ids = owned_customer_ids(db)
    query = db.query(FraudAlert).filter(FraudAlert.account_id.in_(ids) if ids else FraudAlert.id == "")
    if status:
        query = query.filter(FraudAlert.status == status.upper())
    if risk_level:
        query = query.filter(FraudAlert.risk_level == risk_level.upper())
    total = query.count()
    rows = (
        query.order_by(FraudAlert.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    names = account_names(db)
    return {
        "items": [present_alert(db, row, names) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{alert_id}")
def get_alert(alert_id: str, db: Session = Depends(get_db)):
    ids = set(owned_customer_ids(db))
    alert = db.get(FraudAlert, alert_id)
    if alert is None or alert.account_id not in ids:
        raise AppError("ALERT_NOT_FOUND", "Alert was not found", 404)
    return present_alert(db, alert)


@router.patch("/{alert_id}")
def patch_alert(alert_id: str, payload: AlertUpdate, db: Session = Depends(get_db)):
    current = db.get(FraudAlert, alert_id)
    if current is None:
        raise AppError("ALERT_NOT_FOUND", "Alert was not found", 404)
    status = payload.status or current.status
    note = current.resolution_note if payload.resolution_note is None else payload.resolution_note
    alert = review_alert(db, alert_id, status=status, resolution_note=note)
    return present_alert(db, alert)


@router.post("/{alert_id}/review")
def post_review(alert_id: str, payload: AlertReview, db: Session = Depends(get_db)):
    alert = review_alert(db, alert_id, status=payload.status, resolution_note=payload.resolution_note)
    return present_alert(db, alert)
