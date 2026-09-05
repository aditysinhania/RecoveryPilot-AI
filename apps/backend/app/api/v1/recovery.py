"""Read-only recovery queue APIs. No diagnosis, policy, or Razorpay execution."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import LoggerDep, SessionDep
from app.config.constants import DEFAULT_PAGE_SIZE
from app.core.responses import paginated_body, success_body
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.recovery import (
    RecoveryCaseAuditEvent,
    RecoveryCaseResponse,
    RecoveryQueueItem,
    RecoverySummaryResponse,
    RecoveryTimelineEvent,
)
from app.services import recovery_service
from app.utils.pagination import normalize_page

router = APIRouter(prefix="/recovery", tags=["Recovery"])


@router.get("/queue", response_model=PaginatedResponse[RecoveryQueueItem])
def get_recovery_queue(
    db: SessionDep,
    logger: LoggerDep,
    merchant_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    failure_reason: str | None = Query(default=None),
    customer_segment: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    payment_method: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1),
) -> dict[str, Any]:
    """Paginated Payments Requiring Attention queue.

    Sorted by priority descending, then oldest failed payment first.
    """
    pager = normalize_page(page, page_size)
    logger.info(
        "recovery.queue.start",
        extra={"page": pager.page, "page_size": pager.size},
    )
    items, total = recovery_service.get_recovery_queue(
        db,
        offset=pager.offset,
        limit=pager.size,
        merchant_id=merchant_id,
        status=status,
        failure_reason=failure_reason,
        customer_segment=customer_segment,
        priority=priority,
        payment_method=payment_method,
        date_from=date_from,
        date_to=date_to,
    )
    logger.info("recovery.queue.ok", extra={"total": total})
    return paginated_body(items, page=pager.page, page_size=pager.size, total=total)


@router.get("/summary", response_model=ApiResponse[RecoverySummaryResponse])
def get_recovery_summary(
    db: SessionDep,
    logger: LoggerDep,
    merchant_id: UUID | None = Query(default=None),
) -> dict[str, Any]:
    """Live case counts, revenue at risk, recovered revenue, and recovery rate."""
    logger.info(
        "recovery.summary.start",
        extra={"merchant_id": str(merchant_id) if merchant_id else None},
    )
    data = recovery_service.get_recovery_summary(db, merchant_id)
    logger.info(
        "recovery.summary.ok",
        extra={"open_cases": data.open_cases},
    )
    return success_body(data=data, message="ok")


@router.get(
    "/cases/{recovery_case_id}",
    response_model=ApiResponse[RecoveryCaseResponse],
)
def get_recovery_case(
    recovery_case_id: UUID,
    db: SessionDep,
    logger: LoggerDep,
) -> dict[str, Any]:
    """Case detail: customer, subscription, payment, diagnosis, action, promise."""
    logger.info(
        "recovery.case.start",
        extra={"recovery_case_id": str(recovery_case_id)},
    )
    data = recovery_service.get_recovery_case(db, recovery_case_id)
    logger.info(
        "recovery.case.ok",
        extra={"recovery_case_id": str(recovery_case_id)},
    )
    return success_body(data=data, message="ok")


@router.get(
    "/cases/{recovery_case_id}/timeline",
    response_model=ApiResponse[list[RecoveryTimelineEvent]],
)
def get_recovery_timeline(
    recovery_case_id: UUID,
    db: SessionDep,
    logger: LoggerDep,
) -> dict[str, Any]:
    """Chronological recovery journey, timestamps ascending."""
    logger.info(
        "recovery.timeline.start",
        extra={"recovery_case_id": str(recovery_case_id)},
    )
    data = recovery_service.get_recovery_timeline(db, recovery_case_id)
    logger.info(
        "recovery.timeline.ok",
        extra={
            "recovery_case_id": str(recovery_case_id),
            "event_count": len(data),
        },
    )
    return success_body(data=data, message="ok")


@router.get(
    "/cases/{recovery_case_id}/audit",
    response_model=ApiResponse[list[RecoveryCaseAuditEvent]],
)
def get_recovery_case_audit(
    recovery_case_id: UUID,
    db: SessionDep,
    logger: LoggerDep,
) -> dict[str, Any]:
    """Append-only ``audit_logs`` for one case, newest first. Empty list if none."""
    logger.info(
        "recovery.case.audit.start",
        extra={"recovery_case_id": str(recovery_case_id)},
    )
    data = recovery_service.get_case_audit_events(db, recovery_case_id)
    logger.info(
        "recovery.case.audit.ok",
        extra={
            "recovery_case_id": str(recovery_case_id),
            "event_count": len(data),
        },
    )
    return success_body(data=data, message="ok")
