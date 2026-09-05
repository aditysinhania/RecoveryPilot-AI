"""Recovery action orchestrator APIs. Razorpay Sandbox only; mock communications."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import CorrelationIdDep, LoggerDep, RequestIdDep, SessionDep, SettingsDep
from app.core.responses import success_body
from app.schemas.actions import (
    ActionDashboardResponse,
    ActionExecutionResponse,
    ActionStatusResponse,
)
from app.schemas.common import ApiResponse
from app.services import action_service

router = APIRouter(prefix="/actions", tags=["Actions"])


@router.get("/summary", response_model=ApiResponse[ActionDashboardResponse])
def get_action_summary(
    db: SessionDep,
    logger: LoggerDep,
    merchant_id: UUID | None = Query(default=None),
) -> dict[str, Any]:
    """Scheduled actions, payment links, retries, failed deliveries, scheduler queue."""
    logger.info(
        "actions.summary.start",
        extra={"merchant_id": str(merchant_id) if merchant_id else None},
    )
    data = action_service.dashboard(db, merchant_id)
    logger.info(
        "actions.summary.ok",
        extra={"scheduled_actions_today": data.scheduled_actions_today},
    )
    return success_body(data=data, message="ok")


@router.post("/replay/{execution_id}", response_model=ApiResponse[ActionExecutionResponse])
def replay_action(
    execution_id: UUID,
    db: SessionDep,
    settings: SettingsDep,
    logger: LoggerDep,
    request_id: RequestIdDep,
    correlation_id: CorrelationIdDep,
) -> dict[str, Any]:
    """Idempotent webhook / operator replay of one execution."""
    logger.info("actions.replay.start", extra={"execution_id": str(execution_id)})
    data = action_service.replay(
        db,
        settings,
        execution_id,
        request_id=request_id,
        correlation_id=correlation_id,
    )
    logger.info(
        "actions.replay.ok",
        extra={"execution_id": str(execution_id), "display_status": data.display_status},
    )
    return success_body(data=data, message="ok")


@router.post("/{case_id}/execute", response_model=ApiResponse[ActionExecutionResponse])
def execute_action(
    case_id: UUID,
    db: SessionDep,
    settings: SettingsDep,
    logger: LoggerDep,
    request_id: RequestIdDep,
    correlation_id: CorrelationIdDep,
) -> dict[str, Any]:
    """Execute the current RecoveryPlan against Razorpay Sandbox."""
    logger.info("actions.execute.start", extra={"case_id": str(case_id)})
    data = action_service.execute(
        db,
        settings,
        case_id,
        request_id=request_id,
        correlation_id=correlation_id,
    )
    logger.info(
        "actions.execute.ok",
        extra={"case_id": str(case_id), "execution_id": str(data.execution_id)},
    )
    return success_body(data=data, message="ok")


@router.post("/{case_id}/schedule", response_model=ApiResponse[ActionExecutionResponse])
def schedule_action(
    case_id: UUID,
    db: SessionDep,
    settings: SettingsDep,
    logger: LoggerDep,
    request_id: RequestIdDep,
    correlation_id: CorrelationIdDep,
) -> dict[str, Any]:
    """Schedule WAIT_FOR_PAYDAY / HONOUR_PROMISE_TO_PAY at the plan timestamp."""
    logger.info("actions.schedule.start", extra={"case_id": str(case_id)})
    data = action_service.schedule(
        db,
        settings,
        case_id,
        request_id=request_id,
        correlation_id=correlation_id,
    )
    logger.info(
        "actions.schedule.ok",
        extra={"case_id": str(case_id), "execution_id": str(data.execution_id)},
    )
    return success_body(data=data, message="ok")


@router.get("/{case_id}/status", response_model=ApiResponse[ActionStatusResponse])
def get_action_status(
    case_id: UUID,
    db: SessionDep,
    logger: LoggerDep,
    request_id: RequestIdDep,
    correlation_id: CorrelationIdDep,
) -> dict[str, Any]:
    """Live execution status, payment link, retries, schedule, and delivery."""
    logger.info("actions.status.start", extra={"case_id": str(case_id)})
    data = action_service.status(
        db,
        case_id,
        request_id=request_id,
        correlation_id=correlation_id,
    )
    logger.info("actions.status.ok", extra={"case_id": str(case_id)})
    return success_body(data=data, message="ok")
