"""Merchant authentication, onboarding, and account settings."""

from services.auth.constants import BUSINESS_TYPES
from services.auth.errors import (
    AuthError,
    EmailTakenError,
    InvalidCredentialsError,
    OnboardingError,
    UnauthorizedError,
    WeakPasswordError,
)
from services.auth.models import AuthResult, AuthUserRecord, SessionRecord, TokenPair
from services.auth.tables import ensure_auth_tables

__all__ = [
    "BUSINESS_TYPES",
    "AuthError",
    "AuthResult",
    "AuthUserRecord",
    "EmailTakenError",
    "InvalidCredentialsError",
    "OnboardingError",
    "SessionRecord",
    "TokenPair",
    "UnauthorizedError",
    "WeakPasswordError",
    "ensure_auth_tables",
]
