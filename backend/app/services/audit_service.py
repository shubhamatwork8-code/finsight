from app.models import AuditLog
from app.services.context import current_user_id
from app.utils.ids import next_public_id


def write_audit(db, *, action: str, entity_type: str, entity_id: str, message: str, details: dict | None = None) -> AuditLog:
    entry = AuditLog(
        id=next_public_id(db, AuditLog.id, "AUD"),
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        message=message,
        details=details or {},
        user_id=current_user_id.get(),
    )
    db.add(entry)
    db.flush()
    return entry
