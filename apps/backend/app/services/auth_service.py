"""HTTP adapter over auth, onboarding, and account settings domain services."""

from __future__ import annotations

from uuid import UUID

from database.models.merchant_user import MerchantUser
from services.auth.errors import (
    AuthError,
    EmailTakenError,
    OnboardingError,
    WeakPasswordError,
)
from services.auth.errors import (
    InvalidCredentialsError as DomainInvalidCredentials,
)
from services.auth.errors import (
    UnauthorizedError as DomainUnauthorized,
)
from services.auth.models import AuthResult, AuthUserRecord, OnboardingMerchantRecord, SessionRecord
from services.auth.onboarding import (
    complete_onboarding,
    complete_workspace,
    save_business_type,
    save_merchant_info,
    save_razorpay_keys,
)
from services.auth.service import (
    change_password,
    list_sessions,
    load_user_from_access,
    logout_all,
    refresh_tokens,
)
from services.auth.service import (
    login as domain_login,
)
from services.auth.service import (
    logout as domain_logout,
)
from services.auth.service import (
    signup as domain_signup,
)
from services.auth.service import (
    update_profile as domain_update_profile,
)
from services.auth.settings_service import (
    SettingsSnapshot,
    load_settings,
    update_gemini,
    update_notifications,
    update_razorpay,
)
from services.auth.settings_service import (
    update_profile as settings_update_profile,
)
from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from app.config.settings import Settings
from app.core.exceptions import (
    ConflictError,
    DatabaseUnavailableError,
    InvalidCredentialsError,
    UnauthorizedError,
    ValidationException,
    auth_schema_missing_error,
)
from app.schemas.auth import (
    AuthUserOut,
    OnboardingMerchantOut,
    SessionOut,
    SettingsOut,
    TokenOut,
)


def _map_auth_error(exc: AuthError) -> Exception:
    """Convert domain auth errors into HTTP exceptions."""
    if isinstance(exc, EmailTakenError):
        return ConflictError(exc.message, code=exc.code)
    if isinstance(exc, DomainInvalidCredentials):
        return InvalidCredentialsError(exc.message)
    if isinstance(exc, DomainUnauthorized):
        return UnauthorizedError(exc.message)
    if isinstance(exc, (WeakPasswordError, OnboardingError)):
        return ValidationException(exc.message)
    return ValidationException(exc.message)


def _user_out(row: AuthUserRecord) -> AuthUserOut:
    """Map the domain user DTO onto the HTTP schema."""
    return AuthUserOut(
        id=row.id,
        email=row.email,
        full_name=row.full_name,
        role=row.role,
        merchant_id=row.merchant_id,
        merchant_name=row.merchant_name,
        onboarding_completed=row.onboarding_completed,
        onboarding_step=row.onboarding_step,
        workspace_kind=row.workspace_kind,
    )


def _merchant_out(row: OnboardingMerchantRecord) -> OnboardingMerchantOut:
    """Map the domain merchant DTO onto the HTTP schema."""
    return OnboardingMerchantOut(
        id=row.id,
        merchant_id=row.merchant_id,
        merchant_name=row.merchant_name,
        business_category=row.business_category,
        email=row.email,
        phone=row.phone,
        timezone=row.timezone,
        workspace_kind=row.workspace_kind,
        onboarding_completed=row.onboarding_completed,
        onboarding_step=row.onboarding_step,
    )


def _token_out(result: AuthResult) -> TokenOut:
    """Wrap tokens + user for signup/login/refresh."""
    return TokenOut(
        access_token=result.tokens.access_token,
        refresh_token=result.tokens.refresh_token,
        expires_in=result.tokens.expires_in,
        user=_user_out(result.user),
    )


def _settings_out(row: SettingsSnapshot) -> SettingsOut:
    """Map redacted settings onto the HTTP schema."""
    return SettingsOut(
        merchant_name=row.merchant_name,
        business_category=row.business_category,
        email=row.email,
        phone=row.phone,
        timezone=row.timezone,
        razorpay_key_id=row.razorpay_key_id,
        razorpay_configured=row.razorpay_configured,
        webhook_configured=row.webhook_configured,
        gemini_configured=row.gemini_configured,
        gemini_model=row.gemini_model,
        notify_email_recovery=row.notify_email_recovery,
        notify_email_digest=row.notify_email_digest,
        notify_webhook_failures=row.notify_webhook_failures,
        workspace_kind=row.workspace_kind,
        onboarding_completed=row.onboarding_completed,
    )


def _map_infra(exc: Exception) -> Exception:
    """Turn SQLAlchemy connection/schema failures into HTTP errors."""
    if isinstance(exc, OperationalError):
        return DatabaseUnavailableError()
    if isinstance(exc, ProgrammingError):
        return auth_schema_missing_error()
    if isinstance(exc, IntegrityError):
        return ConflictError("An account with this email already exists.", code="email_taken")
    return exc


def _jwt_kwargs(settings: Settings) -> dict[str, object]:
    """Shared JWT settings passed into the domain service."""
    secret = (settings.jwt_secret or "").strip()
    if not secret:
        raise ValidationException("JWT_SECRET is not configured on the server.")
    return {
        "secret": secret,
        "algorithm": settings.jwt_algorithm,
        "access_minutes": settings.jwt_access_minutes,
        "refresh_days": settings.jwt_refresh_days,
    }


def signup(
    db: Session,
    settings: Settings,
    *,
    email: str,
    password: str,
    full_name: str,
    user_agent: str | None,
    ip_address: str | None,
) -> TokenOut:
    """Create an account and return JWTs."""
    try:
        result = domain_signup(
            db,
            email=email,
            password=password,
            full_name=full_name,
            user_agent=user_agent,
            ip_address=ip_address,
            **_jwt_kwargs(settings),
        )
    except AuthError as exc:
        raise _map_auth_error(exc) from exc
    except (OperationalError, ProgrammingError, IntegrityError) as exc:
        raise _map_infra(exc) from exc
    db.commit()
    return _token_out(result)


def login(
    db: Session,
    settings: Settings,
    *,
    email: str,
    password: str,
    user_agent: str | None,
    ip_address: str | None,
) -> TokenOut:
    """Authenticate and return JWTs."""
    try:
        result = domain_login(
            db,
            email=email,
            password=password,
            user_agent=user_agent,
            ip_address=ip_address,
            **_jwt_kwargs(settings),
        )
    except AuthError as exc:
        raise _map_auth_error(exc) from exc
    except (OperationalError, ProgrammingError, IntegrityError) as exc:
        raise _map_infra(exc) from exc
    db.commit()
    return _token_out(result)


def refresh(
    db: Session,
    settings: Settings,
    refresh_token: str,
    *,
    user_agent: str | None,
    ip_address: str | None,
) -> TokenOut:
    """Rotate refresh token."""
    try:
        result = refresh_tokens(
            db,
            refresh_token,
            user_agent=user_agent,
            ip_address=ip_address,
            **_jwt_kwargs(settings),
        )
    except AuthError as exc:
        raise _map_auth_error(exc) from exc
    except (OperationalError, ProgrammingError, IntegrityError) as exc:
        raise _map_infra(exc) from exc
    db.commit()
    return _token_out(result)


def logout(db: Session, settings: Settings, refresh_token: str) -> None:
    """Revoke a refresh session."""
    try:
        domain_logout(
            db,
            refresh_token,
            secret=settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        )
    except AuthError as exc:
        raise _map_auth_error(exc) from exc
    except (OperationalError, ProgrammingError, IntegrityError) as exc:
        raise _map_infra(exc) from exc
    db.commit()


def me(
    db: Session,
    settings: Settings,
    access_token: str,
) -> tuple[MerchantUser, AuthUserOut, UUID | None]:
    """Load the current user from an access JWT."""
    try:
        user, record = load_user_from_access(
            db,
            access_token,
            secret=settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        )
    except AuthError as exc:
        raise _map_auth_error(exc) from exc
    except (OperationalError, ProgrammingError, IntegrityError) as exc:
        raise _map_infra(exc) from exc
    from services.auth.tokens import decode_token

    sid: UUID | None = None
    payload = decode_token(
        access_token,
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    raw = payload.get("sid")
    if raw:
        try:
            sid = UUID(str(raw))
        except ValueError:
            sid = None
    return user, _user_out(record), sid


def onboard_merchant(db: Session, user: MerchantUser, **kwargs: str) -> AuthUserOut:
    """Onboarding step 1."""
    try:
        record = save_merchant_info(db, user, **kwargs)
    except AuthError as exc:
        raise _map_auth_error(exc) from exc
    db.commit()
    return _user_out(record)


def onboard_business(db: Session, user: MerchantUser, business_type: str) -> AuthUserOut:
    """Onboarding step 2."""
    try:
        record = save_business_type(db, user, business_type=business_type)
    except AuthError as exc:
        raise _map_auth_error(exc) from exc
    db.commit()
    return _user_out(record)


def onboard_razorpay(db: Session, user: MerchantUser, **kwargs: str) -> AuthUserOut:
    """Onboarding step 3."""
    try:
        record = save_razorpay_keys(db, user, **kwargs)
    except AuthError as exc:
        raise _map_auth_error(exc) from exc
    db.commit()
    return _user_out(record)


def onboard_workspace(db: Session, user: MerchantUser, workspace_kind: str) -> AuthUserOut:
    """Onboarding step 4."""
    try:
        record = complete_workspace(db, user, workspace_kind=workspace_kind)
    except AuthError as exc:
        raise _map_auth_error(exc) from exc
    db.commit()
    return _user_out(record)


def onboard_complete(db: Session, user: MerchantUser, **kwargs: str) -> OnboardingMerchantOut:
    """Create or update merchant, settings, and Razorpay keys in one request."""
    try:
        record = complete_onboarding(db, user, **kwargs)
    except AuthError as exc:
        raise _map_auth_error(exc) from exc
    db.commit()
    return _merchant_out(record)


def get_settings(db: Session, user: MerchantUser) -> SettingsOut:
    """Settings snapshot."""
    try:
        return _settings_out(load_settings(db, user))
    except AuthError as exc:
        raise _map_auth_error(exc) from exc


def patch_profile(db: Session, user: MerchantUser, **kwargs: str | None) -> SettingsOut:
    """Profile tab."""
    try:
        snapshot = settings_update_profile(db, user, **kwargs)
    except AuthError as exc:
        raise _map_auth_error(exc) from exc
    db.commit()
    return _settings_out(snapshot)


def patch_razorpay(db: Session, user: MerchantUser, **kwargs: str | None) -> SettingsOut:
    """Razorpay tab."""
    try:
        snapshot = update_razorpay(db, user, **kwargs)
    except AuthError as exc:
        raise _map_auth_error(exc) from exc
    db.commit()
    return _settings_out(snapshot)


def patch_gemini(db: Session, user: MerchantUser, **kwargs: str | None) -> SettingsOut:
    """Gemini tab."""
    try:
        snapshot = update_gemini(db, user, **kwargs)
    except AuthError as exc:
        raise _map_auth_error(exc) from exc
    db.commit()
    return _settings_out(snapshot)


def patch_notifications(db: Session, user: MerchantUser, **kwargs: bool | None) -> SettingsOut:
    """Notifications tab."""
    try:
        snapshot = update_notifications(db, user, **kwargs)
    except AuthError as exc:
        raise _map_auth_error(exc) from exc
    db.commit()
    return _settings_out(snapshot)


def patch_password(
    db: Session,
    user: MerchantUser,
    *,
    current_password: str,
    new_password: str,
) -> None:
    """Security tab: change password."""
    try:
        change_password(db, user, current_password=current_password, new_password=new_password)
    except AuthError as exc:
        raise _map_auth_error(exc) from exc
    db.commit()


def sessions(db: Session, user: MerchantUser, current_session_id: UUID | None) -> list[SessionOut]:
    """Security tab: refresh sessions."""
    rows: list[SessionRecord] = list_sessions(db, user.id, current_session_id)
    return [
        SessionOut(
            id=row.id,
            created_at=row.created_at,
            expires_at=row.expires_at,
            user_agent=row.user_agent,
            ip_address=row.ip_address,
            current=row.current,
        )
        for row in rows
    ]


def revoke_all(db: Session, user: MerchantUser) -> int:
    """Revoke every refresh session."""
    count = logout_all(db, user.id)
    db.commit()
    return count


def update_display_name(db: Session, user: MerchantUser, full_name: str) -> AuthUserOut:
    """Update the operator display name."""
    record = domain_update_profile(db, user, full_name=full_name)
    db.commit()
    return _user_out(record)
