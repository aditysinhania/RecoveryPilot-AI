"""Operations snapshot used by the frontend Operations Status page."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.api.deps import LoggerDep, SettingsDep
from app.core.responses import success_body
from app.db.health import ping_database
from app.db.session import SessionLocal
from app.schemas.common import ApiResponse
from app.schemas.ops import OpsStatusResponse
from app.services.ops_service import ops_status

router = APIRouter(prefix="/ops", tags=["Operations"])


@router.get("/status", response_model=ApiResponse[OpsStatusResponse])
def get_ops_status(
    settings: SettingsDep,
    logger: LoggerDep,
) -> dict[str, Any]:
    """Health, webhook throughput, scheduler queue, and build metadata."""
    logger.info("ops.status.start")
    database_ok = ping_database()
    db = None
    if database_ok:
        try:
            db = SessionLocal()
        except Exception:
            database_ok = False
    try:
        data = ops_status(settings, db, database_ok=database_ok)
    finally:
        if db is not None:
            db.close()
    logger.info("ops.status.ok", extra={"status": data.status})
    return success_body(data=data, message=data.status)
