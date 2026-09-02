"""Liveness probe used by local runs and Docker healthchecks."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Return process liveness. This is not a domain endpoint."""
    return {"status": "ok"}
