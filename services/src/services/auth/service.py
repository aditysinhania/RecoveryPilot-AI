"""Merchant user signup, login, refresh, logout, and profile load."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from database.models.auth_session import AuthSession
from database.models.merchant import Merchant
from database.models.merchant_settings import MerchantSettings
from database.models.merchant_user import MerchantUser
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.auth.constants import (
    ACCESS_TOKEN_MINUTES,
    REFRESH_TOKEN_DAYS,
    ROLE_OWNER,
    TOKEN_TYPE_ACCESS,
    TOKEN_TYPE_REFRESH,
    WORKSPACE_NONE,
)
from services.auth.errors import (
    EmailTakenError,
    InvalidCredentialsError,
    UnauthorizedError,
)
from services.auth.models import AuthResult, AuthUserRecord, SessionRecord, TokenPair
from services.auth.passwords import hash_password, verify_password
from services.auth.tables import ensure_auth_tables
from services.auth.tokens import (
    access_payload,
    decode_token,
    encode_token,
    hash_refresh_token,
    refresh_payload,
)

logger = logging.getLogger(__name__)


def _normalize_email(email: str) -> str:
    """Lowercase and strip. Used as the unique login key."""
    return email.strip().lower()


def _settings_for(db: Session, merchant_id: UUID | None) -> MerchantSettings | None:
    """Load merchant_settings for a tenant, or None when unonboarded."""
    if merchant_id is None:
        return None
    return db.scalar(select(MerchantSettings).where(MerchantSettings.merchant_id == merchant_id))


def to_user_record(db: Session, user: MerchantUser) -> AuthUserRecord:
    """Project ORM user + optional merchant onto the API DTO."""
    merchant: Merchant | None = None
    if user.merchant_id is not None:
        merchant = db.get(Merchant, user.merchant_id)
    row = _settings_for(db, user.merchant_id)
    return AuthUserRecord(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        merchant_id=user.merchant_id,
        merchant_name=merchant.merchant_name if merchant else None,
        onboarding_completed=bool(row.onboarding_completed) if row else False,
        onboarding_step=int(row.onboarding_step) if row else 1,
        workspace_kind=row.workspace_kind if row else WORKSPACE_NONE,
    )


def _issue_tokens(
    db: Session,
    user: MerchantUser,
    *,
    secret: str,
    algorithm: str,
    access_minutes: int,
    refresh_days: int,
    user_agent: str | None,
    ip_address: str | None,
) -> TokenPair:
    """Persist a refresh session and return signed JWTs."""
    session_id = uuid4()
    refresh = encode_token(
        refresh_payload(user.id, session_id),
        secret=secret,
        algorithm=algorithm,
        expires_delta=timedelta(days=refresh_days),
    )
    expires_at = datetime.now(UTC) + timedelta(days=refresh_days)
    db.add(
        AuthSession(
            id=session_id,
            user_id=user.id,
            refresh_token_hash=hash_refresh_token(refresh),
            expires_at=expires_at,
            user_agent=(user_agent or "")[:512] or None,
            ip_address=(ip_address or "")[:64] or None,
        )
    )
    access = encode_token(
        access_payload(user.id, user.email, user.merchant_id, session_id),
        secret=secret,
        algorithm=algorithm,
        expires_delta=timedelta(minutes=access_minutes),
    )
    return TokenPair(
        access_token=access,
        refresh_token=refresh,
        session_id=session_id,
        expires_in=access_minutes * 60,
    )


def signup(
    db: Session,
    *,
    email: str,
    password: str,
    full_name: str,
    secret: str,
    algorithm: str,
    access_minutes: int = ACCESS_TOKEN_MINUTES,
    refresh_days: int = REFRESH_TOKEN_DAYS,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> AuthResult:
    """Create a merchant user with no tenant yet."""
    ensure_auth_tables(db)
    normalized = _normalize_email(email)
    existing = db.scalar(select(MerchantUser).where(MerchantUser.email == normalized))
    if existing is not None:
        raise EmailTakenError()
    user = MerchantUser(
        email=normalized,
        password_hash=hash_password(password),
        full_name=full_name.strip() or "Merchant",
        role=ROLE_OWNER,
        is_active=True,
    )
    db.add(user)
    db.flush()
    tokens = _issue_tokens(
        db,
        user,
        secret=secret,
        algorithm=algorithm,
        access_minutes=access_minutes,
        refresh_days=refresh_days,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    logger.info("auth.signup.ok", extra={"user_id": str(user.id)})
    return AuthResult(user=to_user_record(db, user), tokens=tokens)


def login(
    db: Session,
    *,
    email: str,
    password: str,
    secret: str,
    algorithm: str,
    access_minutes: int = ACCESS_TOKEN_MINUTES,
    refresh_days: int = REFRESH_TOKEN_DAYS,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> AuthResult:
    """Verify credentials and start a new refresh session."""
    ensure_auth_tables(db)
    normalized = _normalize_email(email)
    user = db.scalar(select(MerchantUser).where(MerchantUser.email == normalized))
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        raise InvalidCredentialsError()
    user.last_login_at = datetime.now(UTC)
    tokens = _issue_tokens(
        db,
        user,
        secret=secret,
        algorithm=algorithm,
        access_minutes=access_minutes,
        refresh_days=refresh_days,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    logger.info("auth.login.ok", extra={"user_id": str(user.id)})
    return AuthResult(user=to_user_record(db, user), tokens=tokens)


def load_user_from_access(
    db: Session,
    token: str,
    *,
    secret: str,
    algorithm: str,
) -> tuple[MerchantUser, AuthUserRecord]:
    """Resolve the bearer access token to an active user."""
    ensure_auth_tables(db)
    payload = decode_token(token, secret=secret, algorithm=algorithm)
    if payload.get("typ") != TOKEN_TYPE_ACCESS:
        raise UnauthorizedError("Invalid or expired token")
    try:
        user_id = UUID(str(payload.get("sub")))
    except (TypeError, ValueError) as exc:
        raise UnauthorizedError("Invalid or expired token") from exc
    user = db.get(MerchantUser, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("Invalid or expired token")
    return user, to_user_record(db, user)


def refresh_tokens(
    db: Session,
    refresh_token: str,
    *,
    secret: str,
    algorithm: str,
    access_minutes: int = ACCESS_TOKEN_MINUTES,
    refresh_days: int = REFRESH_TOKEN_DAYS,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> AuthResult:
    """Rotate the refresh session. Old token is revoked."""
    ensure_auth_tables(db)
    payload = decode_token(refresh_token, secret=secret, algorithm=algorithm)
    if payload.get("typ") != TOKEN_TYPE_REFRESH:
        raise UnauthorizedError("Invalid or expired token")
    try:
        session_id = UUID(str(payload.get("sid")))
        user_id = UUID(str(payload.get("sub")))
    except (TypeError, ValueError) as exc:
        raise UnauthorizedError("Invalid or expired token") from exc
    row = db.get(AuthSession, session_id)
    now = datetime.now(UTC)
    expected = hash_refresh_token(refresh_token)
    if (
        row is None
        or row.user_id != user_id
        or row.revoked_at is not None
        or row.expires_at <= now
        or row.refresh_token_hash != expected
    ):
        raise UnauthorizedError("Invalid or expired token")
    row.revoked_at = now
    user = db.get(MerchantUser, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("Invalid or expired token")
    tokens = _issue_tokens(
        db,
        user,
        secret=secret,
        algorithm=algorithm,
        access_minutes=access_minutes,
        refresh_days=refresh_days,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    logger.info("auth.refresh.ok", extra={"user_id": str(user.id), "session_id": str(session_id)})
    return AuthResult(user=to_user_record(db, user), tokens=tokens)


def logout(db: Session, refresh_token: str, *, secret: str, algorithm: str) -> None:
    """Revoke the refresh session. Idempotent when already revoked or unknown."""
    ensure_auth_tables(db)
    try:
        payload = decode_token(refresh_token, secret=secret, algorithm=algorithm)
        session_id = UUID(str(payload.get("sid")))
    except (UnauthorizedError, TypeError, ValueError):
        logger.info("auth.logout.ignored")
        return
    row = db.get(AuthSession, session_id)
    if row is not None and row.revoked_at is None:
        row.revoked_at = datetime.now(UTC)
        logger.info("auth.logout.ok", extra={"session_id": str(session_id)})


def logout_all(db: Session, user_id: UUID) -> int:
    """Revoke every refresh session for the user."""
    ensure_auth_tables(db)
    now = datetime.now(UTC)
    rows = list(db.scalars(select(AuthSession).where(AuthSession.user_id == user_id)))
    count = 0
    for row in rows:
        if row.revoked_at is None:
            row.revoked_at = now
            count += 1
    logger.info("auth.logout_all.ok", extra={"user_id": str(user_id), "revoked": count})
    return count


def change_password(
    db: Session,
    user: MerchantUser,
    *,
    current_password: str,
    new_password: str,
) -> None:
    """Verify the current password, then replace the hash."""
    if not verify_password(current_password, user.password_hash):
        raise InvalidCredentialsError("Current password is incorrect")
    user.password_hash = hash_password(new_password)
    logger.info("auth.password.changed", extra={"user_id": str(user.id)})


def update_profile(db: Session, user: MerchantUser, *, full_name: str) -> AuthUserRecord:
    """Update display name on the user row."""
    user.full_name = full_name.strip() or user.full_name
    if user.merchant_id is not None:
        merchant = db.get(Merchant, user.merchant_id)
        if merchant is not None:
            merchant.email = user.email
    logger.info("auth.profile.updated", extra={"user_id": str(user.id)})
    return to_user_record(db, user)


def list_sessions(
    db: Session,
    user_id: UUID,
    current_session_id: UUID | None,
) -> list[SessionRecord]:
    """Active (non-revoked) refresh sessions, newest first."""
    ensure_auth_tables(db)
    rows = list(
        db.scalars(
            select(AuthSession)
            .where(AuthSession.user_id == user_id)
            .order_by(AuthSession.created_at.desc())
        )
    )
    return [
        SessionRecord(
            id=row.id,
            created_at=row.created_at,
            expires_at=row.expires_at,
            user_agent=row.user_agent,
            ip_address=row.ip_address,
            current=current_session_id is not None and row.id == current_session_id,
        )
        for row in rows
        if row.revoked_at is None
    ]
