"""Merchant onboarding. Combined POST plus four-step routes. Requires JWT."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from services.auth.constants import BUSINESS_TYPES

from app.api.deps import CurrentUserDep, LoggerDep, SessionDep
from app.core.responses import success_body
from app.schemas.auth import (
    AuthUserOut,
    BusinessTypeRequest,
    MerchantInfoRequest,
    OnboardingCompleteRequest,
    OnboardingMerchantOut,
    RazorpayKeysRequest,
    WorkspaceRequest,
)
from app.schemas.common import ApiResponse
from app.services import auth_service

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


@router.get("", response_model=ApiResponse[AuthUserOut])
def onboarding_status(principal: CurrentUserDep) -> dict[str, Any]:
    """Current onboarding step and workspace kind."""
    return success_body(data=principal.user, message="ok")


@router.post("", response_model=ApiResponse[OnboardingMerchantOut])
def complete_onboarding(
    payload: OnboardingCompleteRequest,
    principal: CurrentUserDep,
    db: SessionDep,
    logger: LoggerDep,
) -> dict[str, Any]:
    """Create or update the merchant workspace in one authenticated request."""
    data = auth_service.onboard_complete(
        db,
        principal.orm,
        merchant_name=payload.merchant_name,
        business_category=payload.business_category,
        phone=payload.phone,
        timezone=payload.timezone,
        razorpay_key_id=payload.razorpay_key_id,
        razorpay_key_secret=payload.razorpay_key_secret,
        workspace_type=payload.workspace_type,
        webhook_secret=payload.webhook_secret,
    )
    logger.info(
        "onboarding.complete.ok",
        extra={"merchant_id": str(data.merchant_id), "workspace_kind": data.workspace_kind},
    )
    return success_body(data=data, message="ok")


@router.get("/business-types")
def business_types() -> dict[str, Any]:
    """Allowed business categories for step 2."""
    return success_body(data=list(BUSINESS_TYPES), message="ok")


@router.post("/merchant", response_model=ApiResponse[AuthUserOut])
def step_merchant(
    payload: MerchantInfoRequest,
    principal: CurrentUserDep,
    db: SessionDep,
    logger: LoggerDep,
) -> dict[str, Any]:
    """Step 1: merchant name, phone, timezone."""
    data = auth_service.onboard_merchant(
        db,
        principal.orm,
        merchant_name=payload.merchant_name,
        phone=payload.phone,
        timezone=payload.timezone,
    )
    logger.info("onboarding.merchant.ok", extra={"merchant_id": str(data.merchant_id)})
    return success_body(data=data, message="ok")


@router.post("/business", response_model=ApiResponse[AuthUserOut])
def step_business(
    payload: BusinessTypeRequest,
    principal: CurrentUserDep,
    db: SessionDep,
    logger: LoggerDep,
) -> dict[str, Any]:
    """Step 2: business type."""
    data = auth_service.onboard_business(db, principal.orm, payload.business_type)
    logger.info("onboarding.business.ok")
    return success_body(data=data, message="ok")


@router.post("/razorpay", response_model=ApiResponse[AuthUserOut])
def step_razorpay(
    payload: RazorpayKeysRequest,
    principal: CurrentUserDep,
    db: SessionDep,
    logger: LoggerDep,
) -> dict[str, Any]:
    """Step 3: Razorpay Sandbox keys. Secrets are not logged."""
    data = auth_service.onboard_razorpay(
        db,
        principal.orm,
        key_id=payload.key_id,
        key_secret=payload.key_secret,
        webhook_secret=payload.webhook_secret,
    )
    logger.info("onboarding.razorpay.ok")
    return success_body(data=data, message="ok")


@router.post("/workspace", response_model=ApiResponse[AuthUserOut])
def step_workspace(
    payload: WorkspaceRequest,
    principal: CurrentUserDep,
    db: SessionDep,
    logger: LoggerDep,
) -> dict[str, Any]:
    """Step 4: import demo snapshot or start empty. Does not truncate tables."""
    data = auth_service.onboard_workspace(db, principal.orm, payload.workspace_kind)
    logger.info("onboarding.workspace.ok", extra={"workspace_kind": data.workspace_kind})
    return success_body(data=data, message="ok")
