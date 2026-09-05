"""Startup validation for required environment configuration."""

from __future__ import annotations

import logging

from app.config.constants import ALLOWED_ENVIRONMENTS
from app.config.settings import Settings

logger = logging.getLogger(__name__)


class ConfigurationError(RuntimeError):
    """Raised when required environment variables are missing or invalid."""


def validate_environment(settings: Settings) -> None:
    """Fail fast if DATABASE_URL, API_VERSION, or APP_ENV is unusable.

    Args:
        settings: Loaded application settings.

    Raises:
        ConfigurationError: When a required value is blank or APP_ENV is unknown.
    """
    logger.info("config.validate.start", extra={"app_env": settings.app_env})
    if not settings.database_url.strip():
        raise ConfigurationError("DATABASE_URL is required")
    if not settings.api_version.strip():
        raise ConfigurationError("API_VERSION is required")
    if settings.app_env not in ALLOWED_ENVIRONMENTS:
        allowed = ", ".join(sorted(ALLOWED_ENVIRONMENTS))
        raise ConfigurationError(f"APP_ENV must be one of: {allowed}")
    if settings.is_production and (
        not settings.jwt_secret.strip()
        or settings.jwt_secret.strip()
        in {"dev-only-change-me", "local-dev-jwt-secret-change-me-32b!!"}
        or len(settings.jwt_secret.encode("utf-8")) < 32
    ):
        raise ConfigurationError("JWT_SECRET must be set to a strong value in staging/production")
    logger.info(
        "config.validate.ok",
        extra={"app_env": settings.app_env, "api_version": settings.api_version},
    )
