"""Four-step merchant onboarding. Does not run recovery engines or the simulator."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from database.models.merchant import Merchant
from database.models.merchant_metric import MerchantMetric
from database.models.merchant_settings import MerchantSettings
from database.models.merchant_user import MerchantUser
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.auth.constants import (
    BUSINESS_TYPES,
    DEFAULT_PHONE,
    DEFAULT_TIMEZONE,
    WORKSPACE_DEMO,
    WORKSPACE_EMPTY,
)
from services.auth.errors import OnboardingError
from services.auth.models import AuthUserRecord
from services.auth.service import to_user_record
from services.auth.tables import ensure_auth_tables

logger = logging.getLogger(__name__)


def _settings(db: Session, merchant_id: UUID) -> MerchantSettings:
    """Load or create the settings row for a merchant."""
    row = db.scalar(select(MerchantSettings).where(MerchantSettings.merchant_id == merchant_id))
    if row is None:
        row = MerchantSettings(merchant_id=merchant_id, onboarding_step=1)
        db.add(row)
        db.flush()
    return row


def _require_merchant(user: MerchantUser) -> UUID:
    """Onboarding steps 2–4 need a merchant from step 1."""
    if user.merchant_id is None:
        raise OnboardingError("Complete merchant info first")
    return user.merchant_id


def save_merchant_info(
    db: Session,
    user: MerchantUser,
    *,
    merchant_name: str,
    phone: str,
    timezone: str,
) -> AuthUserRecord:
    """Step 1: create or update the tenant row."""
    ensure_auth_tables(db)
    name = merchant_name.strip()
    if not name:
        raise OnboardingError("Merchant name is required")
    tz = timezone.strip() or DEFAULT_TIMEZONE
    phone_value = phone.strip() or DEFAULT_PHONE
    if user.merchant_id is None:
        merchant = Merchant(
            merchant_name=name,
            business_category="Other",
            email=user.email,
            phone=phone_value,
            timezone=tz,
        )
        db.add(merchant)
        db.flush()
        db.add(MerchantMetric(merchant_id=merchant.id))
        user.merchant_id = merchant.id
        row = _settings(db, merchant.id)
        row.onboarding_step = max(row.onboarding_step, 2)
        logger.info(
            "onboarding.merchant.created",
            extra={"user_id": str(user.id), "merchant_id": str(merchant.id)},
        )
    else:
        merchant = db.get(Merchant, user.merchant_id)
        if merchant is None:
            raise OnboardingError("Merchant record is missing")
        merchant.merchant_name = name
        merchant.phone = phone_value
        merchant.timezone = tz
        merchant.email = user.email
        row = _settings(db, merchant.id)
        row.onboarding_step = max(row.onboarding_step, 2)
        logger.info(
            "onboarding.merchant.updated",
            extra={"user_id": str(user.id), "merchant_id": str(merchant.id)},
        )
    return to_user_record(db, user)


def save_business_type(db: Session, user: MerchantUser, *, business_type: str) -> AuthUserRecord:
    """Step 2: store business category on the merchant."""
    ensure_auth_tables(db)
    merchant_id = _require_merchant(user)
    category = business_type.strip()
    if category not in BUSINESS_TYPES:
        raise OnboardingError("Unknown business type")
    merchant = db.get(Merchant, merchant_id)
    if merchant is None:
        raise OnboardingError("Merchant record is missing")
    merchant.business_category = category
    row = _settings(db, merchant_id)
    row.onboarding_step = max(row.onboarding_step, 3)
    logger.info("onboarding.business.ok", extra={"merchant_id": str(merchant_id)})
    return to_user_record(db, user)


def save_razorpay_keys(
    db: Session,
    user: MerchantUser,
    *,
    key_id: str,
    key_secret: str,
    webhook_secret: str,
) -> AuthUserRecord:
    """Step 3: store Sandbox keys. Values are never logged."""
    ensure_auth_tables(db)
    merchant_id = _require_merchant(user)
    kid = key_id.strip()
    secret = key_secret.strip()
    hook = webhook_secret.strip()
    if not kid or not secret:
        raise OnboardingError("Razorpay key id and secret are required")
    row = _settings(db, merchant_id)
    row.razorpay_key_id = kid
    row.razorpay_key_secret = secret
    row.razorpay_webhook_secret = hook or None
    row.onboarding_step = max(row.onboarding_step, 4)
    logger.info("onboarding.razorpay.ok", extra={"merchant_id": str(merchant_id)})
    return to_user_record(db, user)


def complete_workspace(
    db: Session,
    user: MerchantUser,
    *,
    workspace_kind: str,
) -> AuthUserRecord:
    """Step 4: choose demo snapshot vs empty tenant. Does not truncate tables."""
    ensure_auth_tables(db)
    merchant_id = _require_merchant(user)
    kind = workspace_kind.strip().lower()
    if kind not in {WORKSPACE_DEMO, WORKSPACE_EMPTY}:
        raise OnboardingError("Workspace must be demo or empty")
    row = _settings(db, merchant_id)
    if row.onboarding_step < 4:
        raise OnboardingError("Complete Razorpay keys first")
    row.workspace_kind = kind
    row.onboarding_completed = True
    row.onboarding_completed_at = datetime.now(UTC)
    row.onboarding_step = 4
    logger.info(
        "onboarding.workspace.ok",
        extra={"merchant_id": str(merchant_id), "workspace_kind": kind},
    )
    return to_user_record(db, user)
