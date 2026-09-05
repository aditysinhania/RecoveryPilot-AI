"""Account settings routes. Requires a valid access token."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.api.deps import CurrentUserDep, LoggerDep, SessionDep
from app.core.responses import success_body
from app.schemas.auth import (
    GeminiUpdateRequest,
    NotificationsUpdateRequest,
    PasswordChangeRequest,
    ProfileUpdateRequest,
    RazorpayUpdateRequest,
    SessionOut,
    SettingsOut,
)
from app.schemas.common import ApiResponse
from app.services import auth_service

router = APIRouter(prefix="/account", tags=["Account"])


@router.get("/settings", response_model=ApiResponse[SettingsOut])
def get_settings(principal: CurrentUserDep, db: SessionDep) -> dict[str, Any]:
    """Redacted Settings snapshot."""
    data = auth_service.get_settings(db, principal.orm)
    return success_body(data=data, message="ok")


@router.patch("/settings/profile", response_model=ApiResponse[SettingsOut])
def patch_profile(
    payload: ProfileUpdateRequest,
    principal: CurrentUserDep,
    db: SessionDep,
    logger: LoggerDep,
) -> dict[str, Any]:
    """Update merchant profile fields."""
    data = auth_service.patch_profile(
        db,
        principal.orm,
        merchant_name=payload.merchant_name,
        phone=payload.phone,
        timezone=payload.timezone,
        full_name=payload.full_name,
    )
    logger.info("account.profile.ok", extra={"user_id": str(principal.user.id)})
    return success_body(data=data, message="ok")


@router.patch("/settings/razorpay", response_model=ApiResponse[SettingsOut])
def patch_razorpay(
    payload: RazorpayUpdateRequest,
    principal: CurrentUserDep,
    db: SessionDep,
    logger: LoggerDep,
) -> dict[str, Any]:
    """Replace Razorpay Sandbox keys when provided."""
    data = auth_service.patch_razorpay(
        db,
        principal.orm,
        key_id=payload.key_id,
        key_secret=payload.key_secret,
        webhook_secret=payload.webhook_secret,
    )
    logger.info("account.razorpay.ok")
    return success_body(data=data, message="ok")


@router.patch("/settings/gemini", response_model=ApiResponse[SettingsOut])
def patch_gemini(
    payload: GeminiUpdateRequest,
    principal: CurrentUserDep,
    db: SessionDep,
    logger: LoggerDep,
) -> dict[str, Any]:
    """Store a merchant Gemini key. Recovery engines still read process env."""
    data = auth_service.patch_gemini(
        db,
        principal.orm,
        api_key=payload.api_key,
        model=payload.model,
    )
    logger.info("account.gemini.ok")
    return success_body(data=data, message="ok")


@router.patch("/settings/notifications", response_model=ApiResponse[SettingsOut])
def patch_notifications(
    payload: NotificationsUpdateRequest,
    principal: CurrentUserDep,
    db: SessionDep,
    logger: LoggerDep,
) -> dict[str, Any]:
    """Toggle notification preferences."""
    data = auth_service.patch_notifications(
        db,
        principal.orm,
        notify_email_recovery=payload.notify_email_recovery,
        notify_email_digest=payload.notify_email_digest,
        notify_webhook_failures=payload.notify_webhook_failures,
    )
    logger.info("account.notifications.ok")
    return success_body(data=data, message="ok")


@router.post("/settings/password")
def change_password(
    payload: PasswordChangeRequest,
    principal: CurrentUserDep,
    db: SessionDep,
    logger: LoggerDep,
) -> dict[str, Any]:
    """Change the operator password."""
    auth_service.patch_password(
        db,
        principal.orm,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
    logger.info("account.password.ok", extra={"user_id": str(principal.user.id)})
    return success_body(data={"updated": True}, message="ok")


@router.get("/sessions", response_model=ApiResponse[list[SessionOut]])
def list_sessions(principal: CurrentUserDep, db: SessionDep) -> dict[str, Any]:
    """Active refresh sessions for the Security tab."""
    data = auth_service.sessions(db, principal.orm, principal.session_id)
    return success_body(data=data, message="ok")


@router.post("/sessions/revoke-all")
def revoke_all(principal: CurrentUserDep, db: SessionDep, logger: LoggerDep) -> dict[str, Any]:
    """Revoke every refresh session for this operator."""
    count = auth_service.revoke_all(db, principal.orm)
    logger.info("account.sessions.revoked", extra={"count": count})
    return success_body(data={"revoked": count}, message="ok")
