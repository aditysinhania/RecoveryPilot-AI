"""Merchant placeholders. No database queries in this phase."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.api.deps import MerchantDep
from app.core.responses import success_body

router = APIRouter(prefix="/merchants", tags=["Merchants"])


@router.get("")
def list_merchants(_merchant: MerchantDep) -> dict[str, Any]:
    """Return a sample merchant list for OpenAPI and frontend wiring."""
    return success_body(
        message="placeholder",
        data=[
            {
                "id": "00000000-0000-4000-8000-000000000001",
                "merchant_name": "FitLife Gym",
                "business_category": "Fitness & Wellness",
                "timezone": "Asia/Kolkata",
            }
        ],
    )


@router.get("/me")
def current_merchant(_merchant: MerchantDep) -> dict[str, Any]:
    """Placeholder for the authenticated merchant. Auth is not implemented yet."""
    return success_body(
        message="placeholder",
        data={
            "id": "00000000-0000-4000-8000-000000000001",
            "merchant_name": "FitLife Gym",
            "authenticated": False,
        },
    )
