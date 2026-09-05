"""Read-only audit and compliance replay APIs. No AI or Razorpay execution."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import LoggerDep, SessionDep
from app.config.constants import DEFAULT_PAGE_SIZE
from app.core.responses import paginated_body, success_body
from app.schemas.audit import (
    AuditEventResponse,
    AuditTimelineResponse,
    CorrelationTraceResponse,
    PolicyDecisionResponse,
)
from app.schemas.common import ApiResponse, PaginatedResponse
from app.services import audit_service
from app.utils.pagination import normalize_page

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("/events", response_model=PaginatedResponse[AuditEventResponse])
def list_audit_events(
    db: SessionDep,
    logger: LoggerDep,
    event_type: str | None = Query(default=None),
    actor: str | None = Query(default=None),
    recovery_case_id: UUID | None = Query(default=None),
    correlation_id: str | None = Query(default=None),
    request_id: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1),
) -> dict[str, Any]:
    """Paginated audit explorer. Newest events first."""
    pager = normalize_page(page, page_size)
    logger.info(
        "audit.events.start",
        extra={"page": pager.page, "page_size": pager.size},
    )
    items, total = audit_service.get_audit_events(
        db,
        offset=pager.offset,
        limit=pager.size,
        event_type=event_type,
        actor=actor,
        recovery_case_id=recovery_case_id,
        correlation_id=correlation_id,
        request_id=request_id,
        date_from=date_from,
        date_to=date_to,
    )
    logger.info("audit.events.ok", extra={"total": total})
    return paginated_body(items, page=pager.page, page_size=pager.size, total=total)


@router.get(
    "/correlation/{correlation_id}",
    response_model=ApiResponse[CorrelationTraceResponse],
)
def get_correlation_trace(
    correlation_id: str,
    db: SessionDep,
    logger: LoggerDep,
) -> dict[str, Any]:
    """Replay every event for one recovery workflow correlation id."""
    logger.info("audit.correlation.start", extra={"correlation_id": correlation_id})
    data = audit_service.get_correlation_trace(db, correlation_id)
    logger.info(
        "audit.correlation.ok",
        extra={"correlation_id": correlation_id, "event_count": data.event_count},
    )
    return success_body(data=data, message="ok")


@router.get(
    "/cases/{recovery_case_id}",
    response_model=ApiResponse[AuditTimelineResponse],
)
def get_case_audit_timeline(
    recovery_case_id: UUID,
    db: SessionDep,
    logger: LoggerDep,
) -> dict[str, Any]:
    """Chronological compliance timeline from payment failure to outcome."""
    logger.info(
        "audit.timeline.start",
        extra={"recovery_case_id": str(recovery_case_id)},
    )
    data = audit_service.get_case_audit_timeline(db, recovery_case_id)
    logger.info(
        "audit.timeline.ok",
        extra={
            "recovery_case_id": str(recovery_case_id),
            "event_count": data.event_count,
        },
    )
    return success_body(data=data, message="ok")


@router.get(
    "/cases/{recovery_case_id}/policy",
    response_model=ApiResponse[list[PolicyDecisionResponse]],
)
def get_policy_decisions(
    recovery_case_id: UUID,
    db: SessionDep,
    logger: LoggerDep,
) -> dict[str, Any]:
    """Policy-gate evaluations for a case. Placeholder ALLOW if none exist."""
    logger.info(
        "audit.policy.start",
        extra={"recovery_case_id": str(recovery_case_id)},
    )
    data = audit_service.get_policy_decisions(db, recovery_case_id)
    logger.info(
        "audit.policy.ok",
        extra={
            "recovery_case_id": str(recovery_case_id),
            "decision_count": len(data),
        },
    )
    return success_body(data=data, message="ok")
