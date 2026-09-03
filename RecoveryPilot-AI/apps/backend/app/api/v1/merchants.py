"""Read-only merchant dashboard APIs. No recovery execution."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import LoggerDep, MerchantDep, SessionDep
from app.config.constants import DEFAULT_PAGE_SIZE
from app.core.responses import paginated_body, success_body
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.merchant_dashboard import (
    FailureListItem,
    MerchantMetricsPayload,
    MerchantSummary,
    PaymentListItem,
)
from app.services import merchant_service
from app.utils.pagination import normalize_page

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


@router.get(
    "/{merchant_id}/summary",
    response_model=ApiResponse[MerchantSummary],
)
def get_merchant_summary(
    merchant_id: UUID,
    db: SessionDep,
    logger: LoggerDep,
) -> dict[str, Any]:
    """Dashboard header: profile, live ledger counts, and metrics snapshot."""
    logger.info("merchant.summary.start", extra={"merchant_id": str(merchant_id)})
    data = merchant_service.get_summary(db, merchant_id)
    logger.info("merchant.summary.ok", extra={"merchant_id": str(merchant_id)})
    return success_body(data=data, message="ok")


@router.get(
    "/{merchant_id}/metrics",
    response_model=ApiResponse[MerchantMetricsPayload],
)
def get_merchant_metrics(
    merchant_id: UUID,
    db: SessionDep,
    logger: LoggerDep,
) -> dict[str, Any]:
    """Precomputed KPI snapshot. Zeros when no metrics row exists yet."""
    logger.info("merchant.metrics.start", extra={"merchant_id": str(merchant_id)})
    data = merchant_service.get_metrics(db, merchant_id)
    logger.info("merchant.metrics.ok", extra={"merchant_id": str(merchant_id)})
    return success_body(data=data, message="ok")


@router.get(
    "/{merchant_id}/payments",
    response_model=PaginatedResponse[PaymentListItem],
)
def list_merchant_payments(
    merchant_id: UUID,
    db: SessionDep,
    logger: LoggerDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1),
) -> dict[str, Any]:
    """Paginated payment ledger for the merchant, newest first."""
    pager = normalize_page(page, page_size)
    logger.info(
        "merchant.payments.start",
        extra={
            "merchant_id": str(merchant_id),
            "page": pager.page,
            "page_size": pager.size,
        },
    )
    items, total = merchant_service.list_payments(
        db,
        merchant_id,
        offset=pager.offset,
        limit=pager.size,
    )
    logger.info(
        "merchant.payments.ok",
        extra={"merchant_id": str(merchant_id), "total": total},
    )
    return paginated_body(
        items,
        page=pager.page,
        page_size=pager.size,
        total=total,
    )


@router.get(
    "/{merchant_id}/failures",
    response_model=PaginatedResponse[FailureListItem],
)
def list_merchant_failures(
    merchant_id: UUID,
    db: SessionDep,
    logger: LoggerDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1),
) -> dict[str, Any]:
    """Paginated failed-payment queue for the merchant, newest first."""
    pager = normalize_page(page, page_size)
    logger.info(
        "merchant.failures.start",
        extra={
            "merchant_id": str(merchant_id),
            "page": pager.page,
            "page_size": pager.size,
        },
    )
    items, total = merchant_service.list_failures(
        db,
        merchant_id,
        offset=pager.offset,
        limit=pager.size,
    )
    logger.info(
        "merchant.failures.ok",
        extra={"merchant_id": str(merchant_id), "total": total},
    )
    return paginated_body(
        items,
        page=pager.page,
        page_size=pager.size,
        total=total,
    )
