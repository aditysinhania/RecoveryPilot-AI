"""Centralized constants. Routers and middleware must not hardcode these."""

from __future__ import annotations

API_PREFIX: str = "/api/v1"
API_TITLE: str = "RecoveryPilot AI Backend"
API_DESCRIPTION: str = "AI Revenue Recovery Agent for Razorpay Track 03"
API_DOCS_URL: str = "/docs"
API_REDOC_URL: str = "/redoc"
API_OPENAPI_URL: str = "/openapi.json"

DEFAULT_TIMEZONE: str = "Asia/Kolkata"
DEFAULT_CURRENCY: str = "INR"
MAX_BATCH_SIZE: int = 500
DEFAULT_PAGE_SIZE: int = 25
MAX_PAGE_SIZE: int = 100

POOL_SIZE: int = 5
POOL_MAX_OVERFLOW: int = 10
POOL_RECYCLE_SECONDS: int = 1800

REQUEST_ID_HEADER: str = "X-Request-ID"
CORRELATION_ID_HEADER: str = "X-Correlation-ID"
GZIP_MINIMUM_BYTES: int = 500

ALLOWED_ENVIRONMENTS: frozenset[str] = frozenset(
    {"local", "development", "staging", "production"}
)

OPENAPI_TAGS: list[dict[str, str]] = [
    {"name": "Health", "description": "Liveness (/live) and readiness (/ready) probes."},
    {"name": "Merchants", "description": "Read-only merchant dashboard APIs."},
    {"name": "Recovery", "description": "Read-only recovery queue, case, timeline, and summary APIs."},
    {"name": "Audit", "description": "Audit replay placeholders."},
    {"name": "Simulator", "description": "Batch simulator placeholders."},
]
