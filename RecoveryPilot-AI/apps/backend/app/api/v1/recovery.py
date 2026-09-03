"""Recovery placeholders. Diagnosis and execution are not implemented here."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.core.responses import success_body

router = APIRouter(prefix="/recovery", tags=["Recovery"])


@router.get("/cases")
def list_cases() -> dict[str, Any]:
    """Return an empty recovery queue sample."""
    return success_body(
        message="placeholder",
        data={"cases": [], "note": "Recovery planner is not implemented in Phase 4A."},
    )


@router.get("/cases/{case_id}")
def get_case(case_id: str) -> dict[str, Any]:
    """Return a sample case envelope. No database lookup yet."""
    return success_body(
        message="placeholder",
        data={
            "id": case_id,
            "recovery_status": "OPEN",
            "note": "AI diagnosis is not implemented in Phase 4A.",
        },
    )
