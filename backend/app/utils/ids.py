from sqlalchemy.orm import Session


def next_public_id(db: Session, column, prefix: str) -> str:
    values = db.query(column).all()
    numbers = []
    token = f"{prefix}-"
    for (value,) in values:
        if not isinstance(value, str) or not value.startswith(token):
            continue
        suffix = value[len(token) :]
        if suffix.isdigit():
            numbers.append(int(suffix))
    nxt = max(numbers) + 1 if numbers else 1001
    return f"{prefix}-{nxt}"
