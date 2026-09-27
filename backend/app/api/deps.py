from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import AppError
from app.models import User
from app.services.context import current_user_id
from app.services.security import read_token


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError("UNAUTHORIZED", "Sign in to continue.", 401)
    user_id = read_token(authorization.split(" ", 1)[1].strip())
    user = db.get(User, user_id)
    if user is None:
        raise AppError("UNAUTHORIZED", "Sign in to continue.", 401)
    current_user_id.set(user.id)
    return user
