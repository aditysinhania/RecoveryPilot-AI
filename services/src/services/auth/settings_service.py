"""Settings-page updates. Recovery engines still read process environment."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from database.models.merchant import Merchant
from database.models.merchant_settings import MerchantSettings
from database.models.merchant_user import MerchantUser
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.auth.errors import OnboardingError
from services.auth.tables import ensure_auth_tables

logger = logging.getLogger(__name__)


def _mask(value: str | None) -> str | None:
    """Return a redacted preview. Never echo the full secret."""
    if not value:
        return None
    if len(value) <= 4:
        return "****"
    return f"{value[:4]}…{value[-4:]}"


@dataclass(frozen=True)
class SettingsSnapshot:
    """Redacted settings for the Settings page."""

    merchant_name: str
    business_category: str
    email: str
    phone: str
    timezone: str
    razorpay_key_id: str | None
    razorpay_configured: bool
    webhook_configured: bool
    gemini_configured: bool
    gemini_model: str | None
    notify_email_recovery: bool
    notify_email_digest: bool
    notify_webhook_failures: bool
    workspace_kind: str
    onboarding_completed: bool


def _row(db: Session, merchant_id: UUID) -> MerchantSettings:
    """Load settings or fail if onboarding never created them."""
    row = db.scalar(select(MerchantSettings).where(MerchantSettings.merchant_id == merchant_id))
    if row is None:
        raise OnboardingError("Complete onboarding before opening settings")
    return row


def load_settings(db: Session, user: MerchantUser) -> SettingsSnapshot:
    """Return redacted merchant settings."""
    ensure_auth_tables(db)
    if user.merchant_id is None:
        raise OnboardingError("Complete onboarding before opening settings")
    merchant = db.get(Merchant, user.merchant_id)
    if merchant is None:
        raise OnboardingError("Merchant record is missing")
    row = _row(db, user.merchant_id)
    return SettingsSnapshot(
        merchant_name=merchant.merchant_name,
        business_category=merchant.business_category,
        email=merchant.email,
        phone=merchant.phone,
        timezone=merchant.timezone,
        razorpay_key_id=_mask(row.razorpay_key_id),
        razorpay_configured=bool(row.razorpay_key_id and row.razorpay_key_secret),
        webhook_configured=bool(row.razorpay_webhook_secret),
        gemini_configured=bool(row.gemini_api_key),
        gemini_model=row.gemini_model,
        notify_email_recovery=row.notify_email_recovery,
        notify_email_digest=row.notify_email_digest,
        notify_webhook_failures=row.notify_webhook_failures,
        workspace_kind=row.workspace_kind,
        onboarding_completed=row.onboarding_completed,
    )


def update_profile(
    db: Session,
    user: MerchantUser,
    *,
    merchant_name: str | None,
    phone: str | None,
    timezone: str | None,
    full_name: str | None,
) -> SettingsSnapshot:
    """Update merchant profile fields used by the Settings Profile tab."""
    ensure_auth_tables(db)
    if user.merchant_id is None:
        raise OnboardingError("Complete onboarding before opening settings")
    merchant = db.get(Merchant, user.merchant_id)
    if merchant is None:
        raise OnboardingError("Merchant record is missing")
    if merchant_name is not None and merchant_name.strip():
        merchant.merchant_name = merchant_name.strip()
    if phone is not None and phone.strip():
        merchant.phone = phone.strip()
    if timezone is not None and timezone.strip():
        merchant.timezone = timezone.strip()
    if full_name is not None and full_name.strip():
        user.full_name = full_name.strip()
    logger.info("settings.profile.ok", extra={"merchant_id": str(user.merchant_id)})
    return load_settings(db, user)


def update_razorpay(
    db: Session,
    user: MerchantUser,
    *,
    key_id: str | None,
    key_secret: str | None,
    webhook_secret: str | None,
) -> SettingsSnapshot:
    """Replace Sandbox keys when non-empty values are provided."""
    ensure_auth_tables(db)
    if user.merchant_id is None:
        raise OnboardingError("Complete onboarding before opening settings")
    row = _row(db, user.merchant_id)
    if key_id is not None and key_id.strip():
        row.razorpay_key_id = key_id.strip()
    if key_secret is not None and key_secret.strip():
        row.razorpay_key_secret = key_secret.strip()
    if webhook_secret is not None and webhook_secret.strip():
        row.razorpay_webhook_secret = webhook_secret.strip()
    logger.info("settings.razorpay.ok", extra={"merchant_id": str(user.merchant_id)})
    return load_settings(db, user)


def update_gemini(
    db: Session,
    user: MerchantUser,
    *,
    api_key: str | None,
    model: str | None,
) -> SettingsSnapshot:
    """Store a merchant Gemini key for the Settings page. Engines still use env."""
    ensure_auth_tables(db)
    if user.merchant_id is None:
        raise OnboardingError("Complete onboarding before opening settings")
    row = _row(db, user.merchant_id)
    if api_key is not None and api_key.strip():
        row.gemini_api_key = api_key.strip()
    if model is not None and model.strip():
        row.gemini_model = model.strip()
    logger.info("settings.gemini.ok", extra={"merchant_id": str(user.merchant_id)})
    return load_settings(db, user)


def update_notifications(
    db: Session,
    user: MerchantUser,
    *,
    notify_email_recovery: bool | None,
    notify_email_digest: bool | None,
    notify_webhook_failures: bool | None,
) -> SettingsSnapshot:
    """Toggle notification preferences."""
    ensure_auth_tables(db)
    if user.merchant_id is None:
        raise OnboardingError("Complete onboarding before opening settings")
    row = _row(db, user.merchant_id)
    if notify_email_recovery is not None:
        row.notify_email_recovery = notify_email_recovery
    if notify_email_digest is not None:
        row.notify_email_digest = notify_email_digest
    if notify_webhook_failures is not None:
        row.notify_webhook_failures = notify_webhook_failures
    logger.info("settings.notifications.ok", extra={"merchant_id": str(user.merchant_id)})
    return load_settings(db, user)
