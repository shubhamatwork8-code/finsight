from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.services.analytics_service import overview, risk_analytics, transaction_analytics
from app.services.presenters import decimal_text

router = APIRouter(prefix="/analytics", tags=["analytics"], dependencies=[Depends(get_current_user)])


@router.get("/overview")
def get_overview(db: Session = Depends(get_db)):
    payload = overview(db)
    payload["total_balance"] = decimal_text(payload["total_balance"])
    payload["transaction_volume"] = decimal_text(payload["transaction_volume"])
    return payload


@router.get("/transactions")
def get_transaction_analytics(db: Session = Depends(get_db)):
    payload = transaction_analytics(db)
    return {
        "volume_over_time": [
            {"date": point["date"], "amount": decimal_text(point["amount"])} for point in payload["volume_over_time"]
        ],
        "credit_vs_debit": [
            {"type": point["type"], "amount": decimal_text(point["amount"])} for point in payload["credit_vs_debit"]
        ],
        "category_breakdown": [
            {"category": point["category"], "amount": decimal_text(point["amount"])} for point in payload["category_breakdown"]
        ],
    }


@router.get("/risk")
def get_risk_analytics(db: Session = Depends(get_db)):
    payload = risk_analytics(db)
    payload["fraud_by_category"] = [
        {"category": point["category"], "amount": decimal_text(point["amount"])} for point in payload["fraud_by_category"]
    ]
    return payload
