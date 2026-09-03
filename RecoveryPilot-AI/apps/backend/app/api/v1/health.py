"""Health probes. No domain recovery logic."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, status

from app.api.deps import LoggerDep, SettingsDep
from app.core.exceptions import DatabaseUnavailableError
from app.core.responses import success_body
from app.db.health import ping_database
from app.utils.time import isoformat_now

router = APIRouter(tags=["Health"])


@router.get("/live")
def live(settings: SettingsDep, logger: LoggerDep) -> dict[str, Any]:
    """Process liveness. Never queries PostgreSQL.

    Orchestrators use this to decide whether to restart the container.
    """
    logger.info("health.live")
    return success_body(
        message="ok",
        data={
            "status": "ok",
            "environment": settings.app_env,
            "version": settings.api_version,
            "timestamp": isoformat_now(),
        },
    )


@router.get("/ready")
def ready(settings: SettingsDep, logger: LoggerDep) -> dict[str, Any]:
    """Readiness: SQLAlchemy ``SELECT 1``. Raises 503 when Postgres is down."""
    if not ping_database():
        raise DatabaseUnavailableError()
    logger.info("health.ready")
    return success_body(
        message="ok",
        data={
            "status": "ok",
            "environment": settings.app_env,
            "version": settings.api_version,
            "timestamp": isoformat_now(),
            "database": "connected",
        },
    )


@router.get("/health")
def health(settings: SettingsDep, logger: LoggerDep) -> dict[str, Any]:
    """Combined probe: process is up; ``data.database`` reports Postgres.

    Returns HTTP 200 even when Postgres is down so orchestrators can
    distinguish process-up from database-down via the ``database`` field.
    """
    database_ok = ping_database()
    logger.info("health.liveness", extra={"database_ok": database_ok})
    return success_body(
        message="ok" if database_ok else "degraded",
        data={
            "status": "ok" if database_ok else "degraded",
            "environment": settings.app_env,
            "version": settings.api_version,
            "timestamp": isoformat_now(),
            "database": "connected" if database_ok else "unavailable",
        },
    )


@router.get("/health/database", status_code=status.HTTP_200_OK)
def health_database() -> dict[str, Any]:
    """Readiness alias: SQLAlchemy ``SELECT 1``. Raises 503 when Postgres is down."""
    if not ping_database():
        raise DatabaseUnavailableError()
    return success_body(
        message="database connected",
        data={"database": "connected", "timestamp": isoformat_now()},
    )
