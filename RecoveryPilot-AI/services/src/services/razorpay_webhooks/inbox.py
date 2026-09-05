"""Persist Razorpay webhook_events. In-memory for tests; SQLAlchemy for production."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database.models.webhook_event import WebhookEvent
from services.razorpay_webhooks.constants import INGEST_KEY
from services.razorpay_webhooks.models import WebhookSummary

logger = logging.getLogger(__name__)


class DuplicateWebhookError(Exception):
    """Unique ``razorpay_event_id`` already exists in the inbox."""

    def __init__(self, razorpay_event_id: str) -> None:
        self.razorpay_event_id = razorpay_event_id
        super().__init__(f"Duplicate Razorpay event id: {razorpay_event_id}")


class WebhookInboxRecord:
    """One inbox row plus ingest envelope."""

    def __init__(
        self,
        *,
        id: UUID,
        razorpay_event_id: str,
        event_type: str,
        payload: dict[str, Any],
        signature_verified: bool,
        processed_at: datetime | None,
        received_at: datetime,
        replay_count: int = 0,
        failed: bool = False,
    ) -> None:
        self.id = id
        self.razorpay_event_id = razorpay_event_id
        self.event_type = event_type
        self.payload = payload
        self.signature_verified = signature_verified
        self.processed_at = processed_at
        self.received_at = received_at
        self.replay_count = replay_count
        self.failed = failed


class WebhookInbox(Protocol):
    """Idempotent webhook inbox keyed by ``razorpay_event_id``."""

    def get(self, razorpay_event_id: str) -> WebhookInboxRecord | None:
        """Load by provider event id."""
        ...

    def insert(
        self,
        *,
        razorpay_event_id: str,
        event_type: str,
        payload: dict[str, Any],
        signature_verified: bool,
        received_at: datetime,
    ) -> WebhookInboxRecord:
        """Insert a first delivery. Caller must check ``get`` first."""
        ...

    def mark_replay(self, razorpay_event_id: str, *, received_at: datetime) -> WebhookInboxRecord | None:
        """Increment replay count on a duplicate delivery."""
        ...

    def mark_processed(self, razorpay_event_id: str, *, processed_at: datetime) -> None:
        """Set processed_at after dispatch or ignore."""
        ...

    def mark_failed(self, razorpay_event_id: str, *, error: str) -> None:
        """Record a dispatch failure. processed_at stays null."""
        ...

    def summary(self) -> WebhookSummary:
        """Inbox KPIs."""
        ...


def _ingest_of(payload: dict[str, Any]) -> dict[str, Any]:
    """Local envelope stored beside the Razorpay JSON."""
    block = payload.get(INGEST_KEY)
    return block if isinstance(block, dict) else {}


def _with_ingest(payload: dict[str, Any], ingest: dict[str, Any]) -> dict[str, Any]:
    """Copy payload and attach ingest metadata."""
    cloned = dict(payload)
    cloned[INGEST_KEY] = ingest
    return cloned


def _record_from_payload(
    *,
    id: UUID,
    razorpay_event_id: str,
    event_type: str,
    payload: dict[str, Any],
    signature_verified: bool,
    processed_at: datetime | None,
    fallback_received: datetime,
) -> WebhookInboxRecord:
    """Build a record from stored JSON."""
    ingest = _ingest_of(payload)
    received_raw = ingest.get("received_at")
    try:
        received_at = datetime.fromisoformat(str(received_raw)) if received_raw else fallback_received
    except ValueError:
        received_at = fallback_received
    return WebhookInboxRecord(
        id=id,
        razorpay_event_id=razorpay_event_id,
        event_type=event_type,
        payload=payload,
        signature_verified=signature_verified,
        processed_at=processed_at,
        received_at=received_at,
        replay_count=int(ingest.get("replay_count") or 0),
        failed=bool(ingest.get("failed")),
    )


class InMemoryWebhookInbox:
    """Process-local inbox used by unit tests."""

    def __init__(self) -> None:
        self._rows: dict[str, WebhookInboxRecord] = {}

    def get(self, razorpay_event_id: str) -> WebhookInboxRecord | None:
        """Load by provider event id."""
        return self._rows.get(razorpay_event_id)

    def insert(
        self,
        *,
        razorpay_event_id: str,
        event_type: str,
        payload: dict[str, Any],
        signature_verified: bool,
        received_at: datetime,
    ) -> WebhookInboxRecord:
        """Insert a first delivery."""
        ingest = {
            "received_at": received_at.isoformat(),
            "replay_count": 0,
            "failed": False,
        }
        row = WebhookInboxRecord(
            id=uuid4(),
            razorpay_event_id=razorpay_event_id,
            event_type=event_type,
            payload=_with_ingest(payload, ingest),
            signature_verified=signature_verified,
            processed_at=None,
            received_at=received_at,
            replay_count=0,
            failed=False,
        )
        self._rows[razorpay_event_id] = row
        logger.info(
            "webhook.inbox.insert",
            extra={"razorpay_event_id": razorpay_event_id, "event_type": event_type},
        )
        return row

    def mark_replay(self, razorpay_event_id: str, *, received_at: datetime) -> WebhookInboxRecord | None:
        """Increment replay count."""
        row = self._rows.get(razorpay_event_id)
        if row is None:
            return None
        row.replay_count += 1
        ingest = _ingest_of(row.payload)
        ingest["replay_count"] = row.replay_count
        ingest["last_replay_at"] = received_at.isoformat()
        row.payload = _with_ingest(row.payload, ingest)
        logger.info(
            "webhook.inbox.replay",
            extra={"razorpay_event_id": razorpay_event_id, "replay_count": row.replay_count},
        )
        return row

    def mark_processed(self, razorpay_event_id: str, *, processed_at: datetime) -> None:
        """Set processed_at."""
        row = self._rows.get(razorpay_event_id)
        if row is None:
            return
        row.processed_at = processed_at
        ingest = _ingest_of(row.payload)
        ingest["failed"] = False
        row.failed = False
        row.payload = _with_ingest(row.payload, ingest)

    def mark_failed(self, razorpay_event_id: str, *, error: str) -> None:
        """Record dispatch failure."""
        row = self._rows.get(razorpay_event_id)
        if row is None:
            return
        row.failed = True
        ingest = _ingest_of(row.payload)
        ingest["failed"] = True
        ingest["error_type"] = error[:128]
        row.payload = _with_ingest(row.payload, ingest)
        logger.info(
            "webhook.inbox.failed",
            extra={"razorpay_event_id": razorpay_event_id, "error_type": error},
        )

    def summary(self) -> WebhookSummary:
        """Count in-memory rows."""
        received = len(self._rows)
        processed = sum(1 for row in self._rows.values() if row.processed_at is not None)
        replayed = sum(1 for row in self._rows.values() if row.replay_count > 0)
        failed = sum(1 for row in self._rows.values() if row.failed)
        return WebhookSummary(received=received, processed=processed, replayed=replayed, failed=failed)


class SqlAlchemyWebhookInbox:
    """PostgreSQL ``webhook_events`` inbox. Unique ``razorpay_event_id``."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, razorpay_event_id: str) -> WebhookInboxRecord | None:
        """Load by provider event id."""
        row = self._db.scalar(select(WebhookEvent).where(WebhookEvent.razorpay_event_id == razorpay_event_id))
        if row is None:
            return None
        return _record_from_payload(
            id=row.id,
            razorpay_event_id=row.razorpay_event_id,
            event_type=row.event_type,
            payload=dict(row.payload or {}),
            signature_verified=row.signature_verified,
            processed_at=row.processed_at,
            fallback_received=row.created_at,
        )

    def insert(
        self,
        *,
        razorpay_event_id: str,
        event_type: str,
        payload: dict[str, Any],
        signature_verified: bool,
        received_at: datetime,
    ) -> WebhookInboxRecord:
        """Insert a first delivery."""
        ingest = {"received_at": received_at.isoformat(), "replay_count": 0, "failed": False}
        row = WebhookEvent(
            razorpay_event_id=razorpay_event_id,
            event_type=event_type,
            payload=_with_ingest(payload, ingest),
            signature_verified=signature_verified,
            processed_at=None,
            created_at=received_at,
        )
        try:
            with self._db.begin_nested():
                self._db.add(row)
                self._db.flush()
        except IntegrityError as exc:
            logger.info(
                "webhook.inbox.duplicate",
                extra={"razorpay_event_id": razorpay_event_id, "event_type": event_type},
            )
            raise DuplicateWebhookError(razorpay_event_id) from exc
        logger.info(
            "webhook.inbox.insert",
            extra={"razorpay_event_id": razorpay_event_id, "event_type": event_type},
        )
        return _record_from_payload(
            id=row.id,
            razorpay_event_id=row.razorpay_event_id,
            event_type=row.event_type,
            payload=dict(row.payload or {}),
            signature_verified=row.signature_verified,
            processed_at=row.processed_at,
            fallback_received=row.created_at,
        )

    def mark_replay(self, razorpay_event_id: str, *, received_at: datetime) -> WebhookInboxRecord | None:
        """Increment replay count on the existing row."""
        row = self._db.scalar(select(WebhookEvent).where(WebhookEvent.razorpay_event_id == razorpay_event_id))
        if row is None:
            return None
        payload = dict(row.payload or {})
        ingest = _ingest_of(payload)
        ingest["replay_count"] = int(ingest.get("replay_count") or 0) + 1
        ingest["last_replay_at"] = received_at.isoformat()
        row.payload = _with_ingest(payload, ingest)
        self._db.flush()
        logger.info(
            "webhook.inbox.replay",
            extra={"razorpay_event_id": razorpay_event_id, "replay_count": ingest["replay_count"]},
        )
        return _record_from_payload(
            id=row.id,
            razorpay_event_id=row.razorpay_event_id,
            event_type=row.event_type,
            payload=dict(row.payload or {}),
            signature_verified=row.signature_verified,
            processed_at=row.processed_at,
            fallback_received=row.created_at,
        )

    def mark_processed(self, razorpay_event_id: str, *, processed_at: datetime) -> None:
        """Set processed_at after successful dispatch or ignore."""
        row = self._db.scalar(select(WebhookEvent).where(WebhookEvent.razorpay_event_id == razorpay_event_id))
        if row is None:
            return
        row.processed_at = processed_at
        payload = dict(row.payload or {})
        ingest = _ingest_of(payload)
        ingest["failed"] = False
        row.payload = _with_ingest(payload, ingest)
        self._db.flush()

    def mark_failed(self, razorpay_event_id: str, *, error: str) -> None:
        """Record a dispatch failure without setting processed_at."""
        row = self._db.scalar(select(WebhookEvent).where(WebhookEvent.razorpay_event_id == razorpay_event_id))
        if row is None:
            return
        payload = dict(row.payload or {})
        ingest = _ingest_of(payload)
        ingest["failed"] = True
        ingest["error_type"] = error[:128]
        row.payload = _with_ingest(payload, ingest)
        self._db.flush()
        logger.info(
            "webhook.inbox.failed",
            extra={"razorpay_event_id": razorpay_event_id, "error_type": error},
        )

    def summary(self) -> WebhookSummary:
        """Count inbox rows. Replay = ingest.replay_count > 0; failed = ingest.failed."""
        rows = self._db.scalars(select(WebhookEvent)).all()
        received = len(rows)
        processed = 0
        replayed = 0
        failed = 0
        for row in rows:
            if row.processed_at is not None:
                processed += 1
            ingest = _ingest_of(dict(row.payload or {}))
            if int(ingest.get("replay_count") or 0) > 0:
                replayed += 1
            if ingest.get("failed"):
                failed += 1
        return WebhookSummary(received=received, processed=processed, replayed=replayed, failed=failed)
