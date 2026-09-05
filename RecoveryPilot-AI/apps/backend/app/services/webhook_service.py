"""FastAPI adapter over Razorpay webhook ingest. Routers stay thin."""

from __future__ import annotations

from integrations.razorpay import verify_webhook_signature
from services.razorpay_webhook_service import build_webhook_service
from services.razorpay_webhooks.models import WebhookIngestResult, WebhookSummary
from sqlalchemy.orm import Session

from app.core.exceptions import InvalidWebhookSignatureError
from app.core.metrics import record_webhook
from app.db.session import SessionLocal
from app.schemas.webhooks import WebhookIngestResponse, WebhookSummaryResponse
from app.utils.request_id import set_recovery_case_id


def _ingest_response(result: WebhookIngestResult) -> WebhookIngestResponse:
    """Map domain ingest onto the HTTP model."""
    return WebhookIngestResponse(
        razorpay_event_id=result.razorpay_event_id,
        event_type=result.event_type,
        signature_verified=result.signature_verified,
        replayed=result.replayed,
        processed=result.processed,
        failed=result.failed,
        unknown_event=result.unknown_event,
        recovery_case_id=result.recovery_case_id,
        received_at=result.received_at,
        processed_at=result.processed_at,
        message=result.message,
    )


def _summary_response(result: WebhookSummary) -> WebhookSummaryResponse:
    """Map inbox KPIs onto the HTTP model."""
    return WebhookSummaryResponse(
        received=result.received,
        processed=result.processed,
        replayed=result.replayed,
        failed=result.failed,
    )


def ingest_razorpay_webhook(
    *,
    raw_body: bytes,
    signature: str,
    webhook_secret: str,
    request_id: str,
    correlation_id: str,
) -> WebhookIngestResponse:
    """Verify HMAC, persist to webhook_events, dispatch through the orchestrator.

    Signature check runs before a database session is opened so invalid
    deliveries return 401 without touching PostgreSQL.
    """
    if not verify_webhook_signature(raw_body, signature, webhook_secret):
        raise InvalidWebhookSignatureError()
    db = SessionLocal()
    try:
        service = build_webhook_service(db)
        result = service.ingest(raw_body, request_id=request_id, correlation_id=correlation_id)
        db.commit()
        record_webhook(replayed=result.replayed)
        if result.recovery_case_id is not None:
            set_recovery_case_id(str(result.recovery_case_id))
        return _ingest_response(result)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def webhook_summary(db: Session) -> WebhookSummaryResponse:
    """Inbox received / processed / replayed / failed counts."""
    service = build_webhook_service(db)
    return _summary_response(service.summary())
