from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import AuditLog
from app.services.context import current_user_id

router = APIRouter(prefix="/audit-logs", tags=["audit"], dependencies=[Depends(get_current_user)])


@router.get("")
def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(AuditLog).filter(AuditLog.user_id == current_user_id.get())
    total = query.count()
    rows = (
        query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": [
            {
                "id": row.id,
                "action": row.action,
                "entity_type": row.entity_type,
                "entity_id": row.entity_id,
                "message": row.message,
                "details": row.details or {},
                "created_at": row.created_at.isoformat(timespec="seconds"),
            }
            for row in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
