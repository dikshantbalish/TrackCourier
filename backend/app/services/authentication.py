import hashlib
import hmac

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.admin import AdminUser

ADMIN_PASSWORD_MIN_LENGTH = 12
ADMIN_PASSWORD_MAX_LENGTH = 128
password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    if len(password) < ADMIN_PASSWORD_MIN_LENGTH:
        raise ValueError(f"Password must contain at least {ADMIN_PASSWORD_MIN_LENGTH} characters")
    if len(password) > ADMIN_PASSWORD_MAX_LENGTH:
        raise ValueError(f"Password must contain no more than {ADMIN_PASSWORD_MAX_LENGTH} characters")
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    if password_hash.startswith("pbkdf2:"):
        try:
            method, salt, expected = password_hash.split("$", 2)
            _, digest, iterations = method.split(":", 2)
            iteration_count = int(iterations)
            if digest not in {"sha256", "sha512"} or not 1 <= iteration_count <= 2_000_000:
                return False
            actual = hashlib.pbkdf2_hmac(
                digest, password.encode("utf-8"), salt.encode("utf-8"), iteration_count
            ).hex()
            return hmac.compare_digest(actual, expected)
        except (ValueError, TypeError):
            return False

    try:
        return password_hasher.verify(password_hash, password)
    except (InvalidHashError, VerificationError):
        return False


def authenticate_admin(database: Session, username: str, password: str) -> AdminUser | None:
    admin = database.scalar(
        select(AdminUser).where(func.lower(AdminUser.username) == username.strip().lower())
    )
    if admin is None or not verify_password(password, admin.password_hash):
        return None
    if admin.password_hash.startswith("pbkdf2:"):
        admin.password_hash = hash_password(password)
        try:
            database.commit()
        except SQLAlchemyError:
            database.rollback()
            raise
    return admin
