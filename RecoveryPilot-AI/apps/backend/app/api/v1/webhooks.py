"""Inbound Razorpay webhooks. Signature verify, then inbox + orchestrator dispatch."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from app.api.deps import CorrelationIdDep, LoggerDep, RequestIdDep, SessionDep, SettingsDep
from app.core.responses import success_body
from app.schemas.common import ApiResponse
from app.schemas.webhooks import WebhookIngestResponse, WebhookSummaryResponse
from app.services import webhook_service
from integrations.razorpay import SIGNATURE_HEADER

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/razorpay", response_model=ApiResponse[WebhookIngestResponse])
async def post_razorpay_webhook(
    request: Request,
    settings: SettingsDep,
    logger: LoggerDep,
    request_id: RequestIdDep,
    correlation_id: CorrelationIdDep,
) -> dict[str, Any]:
    """Verify ``X-Razorpay-Signature``, persist, and dispatch supported events."""
    raw_body = await request.body()
    signature = request.headers.get(SIGNATURE_HEADER, "")
    logger.info("webhooks.razorpay.start", extra={"bytes": len(raw_body)})
    data = webhook_service.ingest_razorpay_webhook(
        raw_body=raw_body,
        signature=signature,
        webhook_secret=settings.razorpay_webhook_secret,
        request_id=request_id,
        correlation_id=correlation_id,
    )
    logger.info(
        "webhooks.razorpay.ok",
        extra={
            "razorpay_event_id": data.razorpay_event_id,
            "event_type": data.event_type,
            "replayed": data.replayed,
        },
    )
    return success_body(data=data, message=data.message)


@router.get("/summary", response_model=ApiResponse[WebhookSummaryResponse])
def get_webhook_summary(
    db: SessionDep,
    logger: LoggerDep,
) -> dict[str, Any]:
    """Inbox counts: received, processed, replayed, failed."""
    logger.info("webhooks.summary.start")
    data = webhook_service.webhook_summary(db)
    logger.info(
        "webhooks.summary.ok",
        extra={"received": data.received, "replayed": data.replayed},
    )
    return success_body(data=data, message="ok")
