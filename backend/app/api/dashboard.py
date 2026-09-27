from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.services.analytics_service import dashboard_summary
from app.services.presenters import account_names, decimal_text, present_alert, present_transaction

router = APIRouter(prefix="/dashboard", tags=["dashboard"], dependencies=[Depends(get_current_user)])


@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    payload = dashboard_summary(db)
    names = account_names(db)
    return {
        "total_balance": decimal_text(payload["total_balance"]),
        "active_accounts": payload["active_accounts"],
        "transaction_volume": decimal_text(payload["transaction_volume"]),
        "transaction_count": payload["transaction_count"],
        "open_alerts": payload["open_alerts"],
        "high_risk_alerts": payload["high_risk_alerts"],
        "recent_transactions": [present_transaction(db, row, names) for row in payload["recent_transactions"]],
        "attention_queue": [present_alert(db, row, names) for row in payload["attention_queue"]],
        "volume_series": [
            {"date": point["date"], "amount": decimal_text(point["amount"])} for point in payload["volume_series"]
        ],
        "risk_distribution": payload["risk_distribution"],
    }
