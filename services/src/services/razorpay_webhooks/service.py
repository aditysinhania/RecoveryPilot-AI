"""Ingest Razorpay webhooks: verify is done by the caller; this module persists and dispatches."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from services.action_orchestrator.orchestrator import ActionOrchestrator
from services.action_orchestrator.persistence import ActionStore, InMemoryActionStore, SqlAlchemyActionStore
from services.razorpay_webhooks.constants import SUPPORTED_EVENTS
from services.razorpay_webhooks.inbox import (
    DuplicateWebhookError,
    InMemoryWebhookInbox,
    SqlAlchemyWebhookInbox,
    WebhookInbox,
    WebhookInboxRecord,
)
from services.razorpay_webhooks.mapping import event_type_of, razorpay_event_id_of
from services.razorpay_webhooks.models import WebhookIngestResult, WebhookSummary
from services.razorpay_webhooks.resolve import resolve_recovery_case_id
from services.scheduler.service import ActionScheduler

logger = logging.getLogger(__name__)


def _parse_body(raw: bytes) -> dict[str, Any]:
    """Decode JSON bytes into a dict. Invalid JSON becomes a sentinel payload."""
    try:
        parsed = json.loads(raw.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"event": "", "id": "", "payload": {}, "parse_error": True}
    return parsed if isinstance(parsed, dict) else {"event": "", "id": "", "payload": parsed}


class RazorpayWebhookService:
    """Inbox + orchestrator dispatch. Signature checks stay in integrations/."""

    def __init__(
        self,
        inbox: WebhookInbox,
        orchestrator: ActionOrchestrator,
        *,
        db: Session | None = None,
        action_store: ActionStore | None = None,
    ) -> None:
        self._inbox = inbox
        self._orchestrator = orchestrator
        self._db = db
        self._action_store = action_store

    def ingest(
        self,
        raw_body: bytes,
        *,
        request_id: str,
        correlation_id: str,
        as_of: datetime | None = None,
    ) -> WebhookIngestResult:
        """Store one verified delivery, short-circuit duplicates, dispatch supported events.

        Args:
            raw_body: Raw JSON bytes already signature-checked.
            request_id: HTTP request id stamped on audit.
            correlation_id: Workflow correlation id.
            as_of: Clock. Defaults to UTC now.

        Returns:
            Ingest result including replay / unknown / failed flags.
        """
        clock = as_of or datetime.now(UTC)
        body = _parse_body(raw_body)
        event_type = event_type_of(body)
        event_id = razorpay_event_id_of(body) or f"evt-missing-{request_id}"[:128]
        logger.info(
            "webhook.ingest.start",
            extra={"razorpay_event_id": event_id, "event_type": event_type},
        )
        existing = self._inbox.get(event_id)
        if existing is not None:
            return self._replay(
                event_id=event_id,
                event_type=event_type,
                body=body,
                existing=existing,
                request_id=request_id,
                correlation_id=correlation_id,
                clock=clock,
            )
        try:
            stored = self._inbox.insert(
                razorpay_event_id=event_id,
                event_type=event_type or "unknown",
                payload=body,
                signature_verified=True,
                received_at=clock,
            )
        except DuplicateWebhookError:
            existing = self._inbox.get(event_id)
            if existing is None:
                raise
            return self._replay(
                event_id=event_id,
                event_type=event_type,
                body=body,
                existing=existing,
                request_id=request_id,
                correlation_id=correlation_id,
                clock=clock,
            )
        if event_type not in SUPPORTED_EVENTS:
            self._inbox.mark_processed(event_id, processed_at=clock)
            logger.info(
                "webhook.ingest.unknown",
                extra={"razorpay_event_id": event_id, "event_type": event_type},
            )
            return WebhookIngestResult(
                razorpay_event_id=event_id,
                event_type=event_type or "unknown",
                signature_verified=True,
                processed=True,
                unknown_event=True,
                request_id=request_id,
                correlation_id=correlation_id,
                received_at=stored.received_at,
                processed_at=clock,
                message="unknown_event",
            )
        case_id = resolve_recovery_case_id(self._db, body)
        try:
            if case_id is not None:
                self._orchestrator.apply_provider_webhook(
                    recovery_case_id=case_id,
                    provider_event=event_type,
                    razorpay_event_id=event_id,
                    request_id=request_id,
                    correlation_id=correlation_id,
                    as_of=clock,
                )
            self._inbox.mark_processed(event_id, processed_at=clock)
        except Exception as exc:  # noqa: BLE001 — inbox must record the failure
            self._inbox.mark_failed(event_id, error=type(exc).__name__)
            logger.info(
                "webhook.ingest.failed",
                extra={
                    "razorpay_event_id": event_id,
                    "event_type": event_type,
                    "error_type": type(exc).__name__,
                },
            )
            return WebhookIngestResult(
                razorpay_event_id=event_id,
                event_type=event_type,
                signature_verified=True,
                failed=True,
                recovery_case_id=case_id,
                request_id=request_id,
                correlation_id=correlation_id,
                received_at=stored.received_at,
                message="dispatch_failed",
            )
        logger.info(
            "webhook.ingest.ok",
            extra={
                "razorpay_event_id": event_id,
                "event_type": event_type,
                "recovery_case_id": str(case_id) if case_id else None,
            },
        )
        return WebhookIngestResult(
            razorpay_event_id=event_id,
            event_type=event_type,
            signature_verified=True,
            processed=True,
            recovery_case_id=case_id,
            request_id=request_id,
            correlation_id=correlation_id,
            received_at=stored.received_at,
            processed_at=clock,
            message="ok",
        )

    def _replay(
        self,
        *,
        event_id: str,
        event_type: str,
        body: dict[str, Any],
        existing: WebhookInboxRecord,
        request_id: str,
        correlation_id: str,
        clock: datetime,
    ) -> WebhookIngestResult:
        """Idempotent redelivery: increment replay count and append WEBHOOK_REPLAY."""
        replayed = self._inbox.mark_replay(event_id, received_at=clock)
        case_id = resolve_recovery_case_id(self._db, body)
        if case_id is not None:
            self._orchestrator.apply_provider_webhook(
                recovery_case_id=case_id,
                provider_event=event_type,
                razorpay_event_id=event_id,
                request_id=request_id,
                correlation_id=correlation_id,
                as_of=clock,
                replay=True,
            )
        row = replayed or existing
        return WebhookIngestResult(
            razorpay_event_id=event_id,
            event_type=event_type,
            signature_verified=True,
            replayed=True,
            processed=row.processed_at is not None,
            recovery_case_id=case_id,
            request_id=request_id,
            correlation_id=correlation_id,
            received_at=row.received_at,
            processed_at=row.processed_at,
            message="replay",
        )

    def summary(self) -> WebhookSummary:
        """Inbox KPIs: received, processed, replayed, failed."""
        return self._inbox.summary()


def build_webhook_service(
    db: Session | None = None,
    *,
    inbox: WebhookInbox | None = None,
    orchestrator: ActionOrchestrator | None = None,
    action_store: ActionStore | None = None,
    scheduler: ActionScheduler | None = None,
) -> RazorpayWebhookService:
    """Wire inbox + orchestrator. Tests inject in-memory collaborators."""
    store = action_store or (SqlAlchemyActionStore(db) if db is not None else InMemoryActionStore())
    orch = orchestrator or ActionOrchestrator(
        store=store,
        razorpay=_null_razorpay(),
        comms=_null_comms(),
        scheduler=scheduler or ActionScheduler(),
    )
    box = inbox or (SqlAlchemyWebhookInbox(db) if db is not None else InMemoryWebhookInbox())
    return RazorpayWebhookService(box, orch, db=db, action_store=store)


def _null_razorpay() -> Any:
    """Webhook apply does not call Razorpay; a stub satisfies the orchestrator ctor."""
    from services.razorpay_actions.service import RazorpayActionService

    class _NoHttp:
        def create_payment_link(self, payload: dict, *, idempotency_key: str) -> Any:
            raise RuntimeError("webhooks must not call Razorpay")

        def create_order(self, payload: dict, *, idempotency_key: str) -> Any:
            raise RuntimeError("webhooks must not call Razorpay")

        def create_mandate_session(self, payload: dict, *, idempotency_key: str) -> Any:
            raise RuntimeError("webhooks must not call Razorpay")

    return RazorpayActionService(_NoHttp())


def _null_comms() -> Any:
    """Webhook apply does not send customer messages."""
    from services.communications.router import CommunicationRouter

    return CommunicationRouter()
