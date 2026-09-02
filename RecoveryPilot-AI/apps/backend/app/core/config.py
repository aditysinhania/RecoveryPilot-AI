"""Environment-backed application settings."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    """Runtime configuration loaded from `.env` and process environment."""

    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "RecoveryPilot AI"
    app_env: str = "development"
    log_level: str = "INFO"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    cors_origins: str = "http://localhost:5173"
    database_url: str = (
        "postgresql+psycopg://recoverypilot:recoverypilot@localhost:5432/recoverypilot"
    )

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse comma-separated CORS origins from the environment."""
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


settings = Settings()
