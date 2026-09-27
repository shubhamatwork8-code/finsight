import csv
import io
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from app.core.errors import AppError
from app.services.audit_service import write_audit
from app.services.transaction_service import TransactionInput, create_transaction

REQUIRED_COLUMNS = [
    "account_id",
    "transaction_type",
    "amount",
    "currency",
    "merchant",
    "category",
    "description",
    "timestamp",
    "location",
    "destination_account_id",
]


def _parse_timestamp(value: str) -> datetime:
    raw = (value or "").strip()
    if not raw:
        raise AppError("INVALID_TRANSACTION", "Transaction must have a valid timestamp")
    normalized = raw.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise AppError("INVALID_TRANSACTION", "Transaction must have a valid timestamp") from exc
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def import_csv_text(db, content: str) -> dict:
    if not content or not content.strip():
        raise AppError("INVALID_CSV", "CSV file is empty")
    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        raise AppError("INVALID_CSV", "CSV file is missing a header row")
    headers = [name.strip() for name in reader.fieldnames]
    reader.fieldnames = headers
    missing = [column for column in REQUIRED_COLUMNS if column not in headers]
    if missing:
        raise AppError("INVALID_CSV", "CSV is missing required columns: " + ", ".join(missing))

    imported: list[str] = []
    errors: list[dict] = []
    for index, row in enumerate(reader, start=2):
        if row is None or not any((value or "").strip() for value in row.values()):
            continue
        try:
            amount = Decimal(str(row.get("amount", "")).strip())
            payload = TransactionInput(
                account_id=(row.get("account_id") or "").strip(),
                transaction_type=(row.get("transaction_type") or "").strip(),
                amount=amount,
                currency=(row.get("currency") or "").strip(),
                merchant=(row.get("merchant") or "").strip(),
                category=(row.get("category") or "").strip(),
                description=(row.get("description") or "").strip(),
                timestamp=_parse_timestamp(row.get("timestamp") or ""),
                location=(row.get("location") or "").strip() or None,
                destination_account_id=(row.get("destination_account_id") or "").strip() or None,
            )
            transaction = create_transaction(db, payload)
            write_audit(
                db,
                action="TRANSACTION_IMPORTED",
                entity_type="transaction",
                entity_id=transaction.id,
                message=f"Transaction {transaction.id} imported",
            )
            db.commit()
            imported.append(transaction.id)
        except (AppError, InvalidOperation) as exc:
            message = exc.message if isinstance(exc, AppError) else "Amount must be a valid number"
            errors.append({"row": index, "message": message})

    write_audit(
        db,
        action="TRANSACTION_IMPORTED",
        entity_type="import",
        entity_id="CSV",
        message=f"CSV import finished. Imported {len(imported)}. Rejected {len(errors)}.",
        details={"imported": len(imported), "rejected": len(errors)},
    )
    db.commit()
    return {
        "imported": len(imported),
        "rejected": len(errors),
        "errors": errors,
        "transaction_ids": imported,
    }
