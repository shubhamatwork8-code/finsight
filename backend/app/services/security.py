from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jwt import InvalidTokenError

from app.core.config import get_settings
from app.core.errors import AppError

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, stored: str | None) -> bool:
    if not stored:
        return False
    if stored.startswith("pbkdf2_sha256$"):
        return _verify_pbkdf2(password, stored)
    try:
        return _hasher.verify(stored, password)
    except VerifyMismatchError:
        return False


def needs_rehash(stored: str | None) -> bool:
    if not stored:
        return False
    if stored.startswith("pbkdf2_sha256$"):
        return True
    return _hasher.check_needs_rehash(stored)


def _verify_pbkdf2(password: str, stored: str) -> bool:
    import hashlib
    import hmac

    try:
        algorithm, iterations, salt, digest = stored.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iterations)).hex()
    return hmac.compare_digest(check, digest)


def issue_token(user_id: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(days=7)
    return jwt.encode({"sub": user_id, "exp": expires}, get_settings().secret_key, algorithm="HS256")


def read_token(token: str) -> str:
    try:
        payload = jwt.decode(token, get_settings().secret_key, algorithms=["HS256"])
    except InvalidTokenError as exc:
        raise AppError("UNAUTHORIZED", "Sign in to continue.", 401) from exc
    user_id = payload.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise AppError("UNAUTHORIZED", "Sign in to continue.", 401)
    return user_id
