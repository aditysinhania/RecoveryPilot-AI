"""Bcrypt password hashing via passlib. Never log passwords."""

from __future__ import annotations

import logging

import bcrypt

# passlib 1.7 inspects bcrypt.__about__, removed in bcrypt 4.x.
if not hasattr(bcrypt, "__about__"):
    version = getattr(bcrypt, "__version__", "4.0.0")
    bcrypt.__about__ = type("_About", (), {"__version__": version})()

from passlib.context import CryptContext  # noqa: E402

from services.auth.constants import MAX_PASSWORD_BYTES, MIN_PASSWORD_LENGTH
from services.auth.errors import WeakPasswordError

logger = logging.getLogger(__name__)

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Return a bcrypt hash. Rejects empty or oversized secrets."""
    _validate_password(password)
    hashed = _pwd.hash(password)
    logger.info("auth.password.hashed")
    return hashed


def verify_password(password: str, password_hash: str) -> bool:
    """Constant-time bcrypt verify. Returns False on malformed hashes."""
    try:
        return bool(_pwd.verify(password, password_hash))
    except Exception:
        logger.info("auth.password.verify_failed")
        return False


def _validate_password(password: str) -> None:
    """Enforce length rules before hashing."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise WeakPasswordError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise WeakPasswordError("Password is too long for bcrypt (72-byte limit)")
