"""Audit placeholders. Replay logic is not implemented here."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.core.responses import success_body

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("/events")
def list_audit_events() -> dict[str, Any]:
    """Return an empty audit trail sample."""
    return success_body(
        message="placeholder",
        data={"events": [], "note": "Audit replay is not implemented in Phase 4A."},
    )
