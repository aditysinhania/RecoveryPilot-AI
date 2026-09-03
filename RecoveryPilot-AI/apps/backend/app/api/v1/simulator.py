"""Simulator placeholders. Batch evaluation is not invoked here."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.core.responses import success_body

router = APIRouter(prefix="/simulator", tags=["Simulator"])


@router.get("/status")
def simulator_status() -> dict[str, Any]:
    """Return simulator availability without running a generation job."""
    return success_body(
        message="placeholder",
        data={
            "available": True,
            "default_seed": 42,
            "note": "Batch simulator execution is not implemented in Phase 4A.",
        },
    )
