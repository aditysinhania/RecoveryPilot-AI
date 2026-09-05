"""Auth domain DTOs. No ORM objects leave this package."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class AuthUserRecord:
    """Safe user projection for API responses."""

    id: UUID
    email: str
    full_name: str
    role: str
    merchant_id: UUID | None
    merchant_name: str | None
    onboarding_completed: bool
    onboarding_step: int
    workspace_kind: str


@dataclass(frozen=True)
class OnboardingMerchantRecord:
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


@dataclass(frozen=True)
class TokenPair:
    """Access JWT plus refresh JWT and the session row id."""

    access_token: str
    refresh_token: str
    session_id: UUID
    expires_in: int


@dataclass(frozen=True)
class AuthResult:
    """Login / signup / refresh payload."""

    user: AuthUserRecord
    tokens: TokenPair


@dataclass(frozen=True)
class SessionRecord:
    """One refresh session for the Security tab."""

    id: UUID
    created_at: datetime
    expires_at: datetime
    user_agent: str | None
    ip_address: str | None
    current: bool
