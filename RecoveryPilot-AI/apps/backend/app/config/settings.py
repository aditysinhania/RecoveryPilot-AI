"""Environment-backed application settings (Pydantic v2)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.config.constants import ALLOWED_ENVIRONMENTS, POOL_MAX_OVERFLOW, POOL_SIZE

_REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    """Runtime configuration loaded from `.env` and the process environment."""

    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "RecoveryPilot AI"
    app_env: str = "development"
    log_level: str = "INFO"
    api_version: str = "v1"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    cors_origins: str = "http://localhost:5173"
    trusted_hosts: str = "localhost,127.0.0.1,testserver,backend"
    database_url: str = (
        "postgresql+psycopg://recoverypilot:recoverypilot@localhost:5432/recoverypilot"
    )
    db_echo: bool = False
    db_pool_size: int = POOL_SIZE
    db_max_overflow: int = POOL_MAX_OVERFLOW
    razorpay_key_id: str = "rzp_test_placeholder"
    razorpay_key_secret: str = "placeholder_secret"
    gemini_api_key: str = "placeholder_gemini_key"
    gemini_model: str = "gemini-2.5-flash"
    gemini_temperature: float = 0.2
    gemini_max_output_tokens: int = 512

    @field_validator("app_env")
    @classmethod
    def _env_allowed(cls, value: str) -> str:
        """Reject unknown APP_ENV values before the app starts serving."""
        normalized = value.strip().lower()
        if normalized not in ALLOWED_ENVIRONMENTS:
            allowed = ", ".join(sorted(ALLOWED_ENVIRONMENTS))
            raise ValueError(f"APP_ENV must be one of: {allowed}")
        return normalized

    @field_validator("log_level")
    @classmethod
    def _log_level_upper(cls, value: str) -> str:
        """Normalize log level tokens."""
        return value.strip().upper()

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse comma-separated CORS origins from the environment."""
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def trusted_host_list(self) -> list[str]:
        """Parse comma-separated trusted hosts."""
        return [item.strip() for item in self.trusted_hosts.split(",") if item.strip()]

    @property
    def is_production(self) -> bool:
        """True when running in staging or production."""
        return self.app_env in {"staging", "production"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()


settings: Settings = get_settings()
