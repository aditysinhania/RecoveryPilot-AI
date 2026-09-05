"""Settings load and environment validation tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config.constants import ALLOWED_ENVIRONMENTS
from app.config.environment import ConfigurationError, validate_environment
from app.config.settings import Settings, get_settings


def test_settings_load_defaults() -> None:
    """Local defaults include DATABASE_URL, API_VERSION, and a valid APP_ENV."""
    get_settings.cache_clear()
    loaded = Settings()
    assert loaded.database_url.startswith("postgresql")
    assert loaded.api_version
    assert loaded.app_env in ALLOWED_ENVIRONMENTS
    assert loaded.razorpay_key_id
    assert loaded.gemini_api_key


def test_settings_singleton() -> None:
    """``get_settings`` returns a cached instance."""
    get_settings.cache_clear()
    first = get_settings()
    second = get_settings()
    assert first is second


def test_invalid_env_rejected() -> None:
    """APP_ENV outside the allowed set fails validation."""
    with pytest.raises(ValidationError):
        Settings(app_env="qa")


def test_validate_environment_requires_database_url() -> None:
    """Blank DATABASE_URL is rejected at startup validation."""
    loaded = Settings()
    loaded.database_url = "   "
    with pytest.raises(ConfigurationError, match="DATABASE_URL"):
        validate_environment(loaded)
