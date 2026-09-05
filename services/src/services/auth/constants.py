"""Auth and onboarding constants. No HTTP."""

from __future__ import annotations

ROLE_OWNER: str = "owner"
TOKEN_TYPE_ACCESS: str = "access"
TOKEN_TYPE_REFRESH: str = "refresh"
WORKSPACE_NONE: str = "none"
WORKSPACE_DEMO: str = "demo"
WORKSPACE_EMPTY: str = "empty"
WORKSPACE_KINDS: frozenset[str] = frozenset({WORKSPACE_NONE, WORKSPACE_DEMO, WORKSPACE_EMPTY})

MIN_PASSWORD_LENGTH: int = 8
MAX_PASSWORD_BYTES: int = 72
ACCESS_TOKEN_MINUTES: int = 15
REFRESH_TOKEN_DAYS: int = 7

BUSINESS_TYPES: tuple[str, ...] = (
    "Fitness & Wellness",
    "EdTech",
    "SaaS",
    "Media",
    "Healthcare",
    "E-commerce",
    "Other",
)

DEFAULT_TIMEZONE: str = "Asia/Kolkata"
DEFAULT_PHONE: str = "+91"
