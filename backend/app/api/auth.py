from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.errors import AppError
from app.models import User
from app.services.bootstrap import provision_workspace
from app.services.context import current_user_id
from app.services.security import hash_password, issue_token, needs_rehash, verify_password
from app.utils.ids import next_public_id

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterBody(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=180)
    password: str = Field(min_length=8, max_length=128)


class LoginBody(BaseModel):
    email: str
    password: str


def _public_user(user: User) -> dict:
    return {"id": user.id, "email": user.email, "full_name": user.full_name}


def _token_body(user: User) -> dict:
    return {"token": issue_token(user.id), "user": _public_user(user)}


@router.post("/register", status_code=201)
def register(payload: RegisterBody, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise AppError("INVALID_REQUEST", "Enter a valid email address.", 422)
    existing = db.query(User).filter(func.lower(User.email) == email).one_or_none()
    if existing is not None:
        raise AppError("EMAIL_IN_USE", "An account with that email already exists.", 409)
    user = User(
        id=next_public_id(db, User.id, "USR"),
        email=email,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.flush()
    current_user_id.set(user.id)
    provision_workspace(db, user)
    db.commit()
    db.refresh(user)
    return _token_body(user)


@router.post("/login")
def login(payload: LoginBody, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    user = db.query(User).filter(func.lower(User.email) == email).one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise AppError("INVALID_CREDENTIALS", "Email or password is incorrect.", 401)
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)
        db.commit()
    current_user_id.set(user.id)
    return _token_body(user)


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return _public_user(user)
