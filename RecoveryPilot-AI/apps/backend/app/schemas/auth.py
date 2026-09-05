"""Pydantic contracts for auth, onboarding, and account settings."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field
from services.auth.constants import MIN_PASSWORD_LENGTH


class SignupRequest(BaseModel):
    """Create a merchant operator account."""

    email: EmailStr
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)


class LoginRequest(BaseModel):
    """Email + password grant."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    """Rotate an existing refresh JWT."""

    refresh_token: str = Field(min_length=16)


class LogoutRequest(BaseModel):
    """Revoke a refresh JWT."""

    refresh_token: str = Field(min_length=16)


class AuthUserOut(BaseModel):
    """Public user + onboarding projection."""

    id: UUID
    email: str
    full_name: str
    role: str
    merchant_id: UUID | None = None
    merchant_name: str | None = None
    onboarding_completed: bool
    onboarding_step: int
    workspace_kind: str


class TokenOut(BaseModel):
    """JWT pair returned by signup, login, and refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: AuthUserOut


class MerchantInfoRequest(BaseModel):
    """Onboarding step 1."""

    merchant_name: str = Field(min_length=1, max_length=255)
    phone: str = Field(default="", max_length=32)
    timezone: str = Field(default="Asia/Kolkata", max_length=64)


class BusinessTypeRequest(BaseModel):
    """Onboarding step 2."""

    business_type: str = Field(min_length=1, max_length=128)


class RazorpayKeysRequest(BaseModel):
    """Onboarding step 3. Secrets are never echoed."""

    key_id: str = Field(min_length=1, max_length=128)
    key_secret: str = Field(min_length=1, max_length=255)
    webhook_secret: str = Field(default="", max_length=255)


class WorkspaceRequest(BaseModel):
    """Onboarding step 4."""

    workspace_kind: str = Field(pattern="^(demo|empty)$")


class OnboardingCompleteRequest(BaseModel):
    """Single-shot onboarding body for ``POST /api/v1/onboarding``."""

    merchant_name: str = Field(min_length=1, max_length=255)
    business_category: str = Field(min_length=1, max_length=128)
    phone: str = Field(default="", max_length=32)
    timezone: str = Field(default="Asia/Kolkata", max_length=64)
    razorpay_key_id: str = Field(min_length=1, max_length=128)
    razorpay_key_secret: str = Field(min_length=1, max_length=255)
    workspace_type: str = Field(pattern="^(demo|empty)$")
    webhook_secret: str = Field(default="", max_length=255)


class OnboardingMerchantOut(BaseModel):
    """Merchant created or updated by combined onboarding."""

    id: UUID
    merchant_id: UUID
    merchant_name: str
    business_category: str
    email: str
    phone: str
    timezone: str
    workspace_kind: str
    onboarding_completed: bool
    onboarding_step: int


class ProfileUpdateRequest(BaseModel):
    """Settings → Profile."""

    full_name: str | None = Field(default=None, max_length=255)
    merchant_name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    timezone: str | None = Field(default=None, max_length=64)


class RazorpayUpdateRequest(BaseModel):
    """Settings → Razorpay. Empty strings are ignored."""

    key_id: str | None = Field(default=None, max_length=128)
    key_secret: str | None = Field(default=None, max_length=255)
    webhook_secret: str | None = Field(default=None, max_length=255)


class GeminiUpdateRequest(BaseModel):
    """Settings → Gemini."""

    api_key: str | None = Field(default=None, max_length=255)
    model: str | None = Field(default=None, max_length=128)


class NotificationsUpdateRequest(BaseModel):
    """Settings → Notifications."""

    notify_email_recovery: bool | None = None
    notify_email_digest: bool | None = None
    notify_webhook_failures: bool | None = None


class PasswordChangeRequest(BaseModel):
    """Settings → Security."""

    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=128)


class SettingsOut(BaseModel):
    """Redacted settings snapshot."""

    merchant_name: str
    business_category: str
    email: str
    phone: str
    timezone: str
    razorpay_key_id: str | None = None
    razorpay_configured: bool
    webhook_configured: bool
    gemini_configured: bool
    gemini_model: str | None = None
    notify_email_recovery: bool
    notify_email_digest: bool
    notify_webhook_failures: bool
    workspace_kind: str
    onboarding_completed: bool


class SessionOut(BaseModel):
    """One refresh session row."""

    id: UUID
    created_at: datetime
    expires_at: datetime
    user_agent: str | None = None
    ip_address: str | None = None
    current: bool
