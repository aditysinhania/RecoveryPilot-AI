"""Read/write recovery_actions and audit_logs without changing schema or relationships."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import AuditLog, RecoveryAction
from services.action_orchestrator.models import ActionRecord
from shared.enums import (
    ActorType,
    AuditEventType,
    ExecutionStatus,
    PolicyDecision,
    RecoveryActionType,
)

logger = logging.getLogger(__name__)


class ActionStore(Protocol):
    """Persistence port used by the orchestrator and tests."""

    def get(self, execution_id: UUID) -> ActionRecord | None:
        """Load one action by execution id."""
        ...

    def get_by_idempotency(self, key: str) -> ActionRecord | None:
        """Load the action that used this idempotency key."""
        ...

    def list_for_case(self, recovery_case_id: UUID) -> list[ActionRecord]:
        """Newest-first history for a case."""
        ...

    def save(self, record: ActionRecord) -> ActionRecord:
        """Insert or update a recovery_actions row."""
        ...

    def list_due(self, as_of: datetime) -> list[ActionRecord]:
        """SCHEDULED rows whose scheduled_time has arrived."""
        ...

    def append_audit(
        self,
        *,
        recovery_case_id: UUID,
        event_type: AuditEventType,
        summary: str,
        payload: dict[str, Any],
        policy_decision: PolicyDecision | None = None,
        actor_name: str = "ACTION_ORCHESTRATOR",
    ) -> None:
        """Insert one audit_logs row. Never updates existing events."""
        ...

    def dashboard_counts(self, *, merchant_id: UUID | None, as_of: datetime) -> dict[str, int]:
        """Aggregate orchestrator KPIs. Keys match ActionDashboardSummary fields."""
        ...


def _record_from_orm(row: RecoveryAction) -> ActionRecord:
    """Map an ORM row onto the orchestrator record."""
    return ActionRecord(
        id=row.id,
        recovery_case_id=row.recovery_case_id,
        action_type=row.action_type,
        scheduled_time=row.scheduled_time,
        executed_time=row.executed_time,
        execution_status=row.execution_status,
        razorpay_payment_link=row.razorpay_payment_link,
        retry_number=row.retry_number,
        response_code=row.response_code,
        response_message=row.response_message,
        action_metadata=dict(row.action_metadata or {}),
        created_at=row.created_at,
    )


class InMemoryActionStore:
    """Test double. No PostgreSQL."""

    def __init__(self) -> None:
        self.actions: dict[UUID, ActionRecord] = {}
        self.audits: list[dict[str, Any]] = []

    def get(self, execution_id: UUID) -> ActionRecord | None:
        """Load by id."""
        return self.actions.get(execution_id)

    def get_by_idempotency(self, key: str) -> ActionRecord | None:
        """Scan metadata for the idempotency key."""
        for row in self.actions.values():
            if row.action_metadata.get("idempotency_key") == key:
                return row
        return None

    def list_for_case(self, recovery_case_id: UUID) -> list[ActionRecord]:
        """Newest-first."""
        rows = [row for row in self.actions.values() if row.recovery_case_id == recovery_case_id]
        return sorted(rows, key=lambda item: item.created_at or datetime.min.replace(tzinfo=UTC), reverse=True)

    def save(self, record: ActionRecord) -> ActionRecord:
        """Upsert in the dict."""
        stored = record.model_copy(deep=True)
        if stored.created_at is None:
            stored.created_at = datetime.now(UTC)
        self.actions[stored.id] = stored
        return stored

    def list_due(self, as_of: datetime) -> list[ActionRecord]:
        """Scheduled rows that are due."""
        due: list[ActionRecord] = []
        for row in self.actions.values():
            if row.execution_status != ExecutionStatus.SCHEDULED:
                continue
            if row.action_metadata.get("dead_lettered"):
                continue
            if row.scheduled_time is not None and row.scheduled_time <= as_of:
                due.append(row)
        return due

    def append_audit(
        self,
        *,
        recovery_case_id: UUID,
        event_type: AuditEventType,
        summary: str,
        payload: dict[str, Any],
        policy_decision: PolicyDecision | None = None,
        actor_name: str = "ACTION_ORCHESTRATOR",
    ) -> None:
        """Append an in-memory audit event."""
        self.audits.append(
            {
                "recovery_case_id": recovery_case_id,
                "event_type": event_type,
                "summary": summary,
                "payload": payload,
                "policy_decision": policy_decision,
                "actor_name": actor_name,
            }
        )

    def dashboard_counts(self, *, merchant_id: UUID | None, as_of: datetime) -> dict[str, int]:
        """Count from the in-memory rows. merchant_id is ignored in tests."""
        del merchant_id
        start = as_of.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        scheduled_today = 0
        links = 0
        retries = 0
        failed_deliveries = 0
        active = 0
        for row in self.actions.values():
            meta = row.action_metadata
            if row.execution_status == ExecutionStatus.SCHEDULED:
                active += 1
                if row.scheduled_time and row.scheduled_time >= start:
                    scheduled_today += 1
            if row.action_type == RecoveryActionType.GENERATE_PAYMENT_LINK and row.razorpay_payment_link:
                if row.execution_status in {ExecutionStatus.RUNNING, ExecutionStatus.SUCCEEDED}:
                    links += 1
            if (
                row.action_type == RecoveryActionType.RETRY_PAYMENT
                and row.execution_status == ExecutionStatus.SUCCEEDED
            ):
                retries += 1
            delivery = str(meta.get("delivery_status") or "")
            if delivery == "FAILED" or meta.get("dead_lettered"):
                failed_deliveries += 1
        return {
            "scheduled_actions_today": scheduled_today,
            "payment_links_sent": links,
            "successful_retries": retries,
            "failed_deliveries": failed_deliveries,
            "active_scheduler_queue": active,
        }


class SqlAlchemyActionStore:
    """Postgres-backed store using the existing recovery_actions table."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, execution_id: UUID) -> ActionRecord | None:
        """Primary-key lookup."""
        row = self._db.get(RecoveryAction, execution_id)
        return _record_from_orm(row) if row is not None else None

    def get_by_idempotency(self, key: str) -> ActionRecord | None:
        """JSONB contains on metadata.idempotency_key."""
        row = self._db.scalar(
            select(RecoveryAction).where(RecoveryAction.action_metadata.contains({"idempotency_key": key}))
        )
        return _record_from_orm(row) if row is not None else None

    def list_for_case(self, recovery_case_id: UUID) -> list[ActionRecord]:
        """Newest-first history."""
        rows = self._db.scalars(
            select(RecoveryAction)
            .where(RecoveryAction.recovery_case_id == recovery_case_id)
            .order_by(RecoveryAction.created_at.desc())
        ).all()
        return [_record_from_orm(row) for row in rows]

    def save(self, record: ActionRecord) -> ActionRecord:
        """Insert or update. ``record.id`` is the deterministic execution_id."""
        row = self._db.get(RecoveryAction, record.id)
        if row is None:
            row = RecoveryAction(
                id=record.id,
                recovery_case_id=record.recovery_case_id,
                action_type=record.action_type,
                scheduled_time=record.scheduled_time,
                executed_time=record.executed_time,
                execution_status=record.execution_status,
                razorpay_payment_link=record.razorpay_payment_link,
                retry_number=record.retry_number,
                response_code=record.response_code,
                response_message=record.response_message,
                action_metadata=dict(record.action_metadata or {}),
            )
            self._db.add(row)
        else:
            row.action_type = record.action_type
            row.scheduled_time = record.scheduled_time
            row.executed_time = record.executed_time
            row.execution_status = record.execution_status
            row.razorpay_payment_link = record.razorpay_payment_link
            row.retry_number = record.retry_number
            row.response_code = record.response_code
            row.response_message = record.response_message
            row.action_metadata = dict(record.action_metadata or {})
        self._db.flush()
        logger.info(
            "orchestrator.action.save",
            extra={
                "execution_id": str(record.id),
                "recovery_case_id": str(record.recovery_case_id),
                "execution_status": record.execution_status.value,
            },
        )
        return _record_from_orm(row)

    def list_due(self, as_of: datetime) -> list[ActionRecord]:
        """Due SCHEDULED actions."""
        rows = self._db.scalars(
            select(RecoveryAction).where(
                RecoveryAction.execution_status == ExecutionStatus.SCHEDULED,
                RecoveryAction.scheduled_time.is_not(None),
                RecoveryAction.scheduled_time <= as_of,
            )
        ).all()
        return [
            _record_from_orm(row)
            for row in rows
            if not (row.action_metadata or {}).get("dead_lettered")
        ]

    def append_audit(
        self,
        *,
        recovery_case_id: UUID,
        event_type: AuditEventType,
        summary: str,
        payload: dict[str, Any],
        policy_decision: PolicyDecision | None = None,
        actor_name: str = "ACTION_ORCHESTRATOR",
    ) -> None:
        """Insert an append-only audit event with request_id / correlation_id in JSON."""
        self._db.add(
            AuditLog(
                recovery_case_id=recovery_case_id,
                actor_type=ActorType.SYSTEM,
                actor_name=actor_name,
                event_type=event_type,
                event_summary=summary[:1024],
                structured_payload=payload,
                policy_decision=policy_decision,
            )
        )
        self._db.flush()
        logger.info(
            "orchestrator.audit.append",
            extra={
                "recovery_case_id": str(recovery_case_id),
                "event_type": event_type.value,
            },
        )

    def dashboard_counts(self, *, merchant_id: UUID | None, as_of: datetime) -> dict[str, int]:
        """Aggregate from recovery_actions. Optional merchant filter via case join."""
        from database.models import RecoveryCase

        start = as_of.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        query = select(RecoveryAction)
        if merchant_id is not None:
            query = query.join(RecoveryCase, RecoveryAction.recovery_case_id == RecoveryCase.id).where(
                RecoveryCase.merchant_id == merchant_id
            )
        rows = self._db.scalars(query).all()
        scheduled_today = 0
        links = 0
        retries = 0
        failed_deliveries = 0
        active = 0
        for row in rows:
            meta = row.action_metadata or {}
            if row.execution_status == ExecutionStatus.SCHEDULED:
                active += 1
                if row.scheduled_time is not None and row.scheduled_time >= start:
                    scheduled_today += 1
            if row.action_type == RecoveryActionType.GENERATE_PAYMENT_LINK and row.razorpay_payment_link:
                if row.execution_status in {ExecutionStatus.RUNNING, ExecutionStatus.SUCCEEDED}:
                    links += 1
            if (
                row.action_type == RecoveryActionType.RETRY_PAYMENT
                and row.execution_status == ExecutionStatus.SUCCEEDED
            ):
                retries += 1
            delivery = str(meta.get("delivery_status") or "")
            if delivery == "FAILED" or meta.get("dead_lettered"):
                failed_deliveries += 1
        return {
            "scheduled_actions_today": scheduled_today,
            "payment_links_sent": links,
            "successful_retries": retries,
            "failed_deliveries": failed_deliveries,
            "active_scheduler_queue": active,
        }


def chips_for_rows(rows: list[ActionRecord]) -> dict[str, str]:
    """Latest chip per case id (string keys for JSON)."""
    from services.action_orchestrator.mapping import action_chip_for, display_status_for

    latest: dict[UUID, ActionRecord] = {}
    for row in rows:
        current = latest.get(row.recovery_case_id)
        if current is None:
            latest[row.recovery_case_id] = row
            continue
        left = row.created_at or datetime.min.replace(tzinfo=UTC)
        right = current.created_at or datetime.min.replace(tzinfo=UTC)
        if left >= right:
            latest[row.recovery_case_id] = row
    chips: dict[str, str] = {}
    for case_id, row in latest.items():
        display = display_status_for(row.action_metadata, row.execution_status)
        chips[str(case_id)] = action_chip_for(
            display, row.action_type, payment_link=row.razorpay_payment_link
        )
    return chips


def merchant_action_rows(store: SqlAlchemyActionStore, merchant_id: UUID | None) -> list[ActionRecord]:
    """Helper used by dashboard chip map. Best-effort; empty when not SQL store."""
    if not isinstance(store, SqlAlchemyActionStore):
        return list(getattr(store, "actions", {}).values()) if hasattr(store, "actions") else []
    from database.models import RecoveryCase

    query = select(RecoveryAction)
    if merchant_id is not None:
        query = query.join(RecoveryCase, RecoveryAction.recovery_case_id == RecoveryCase.id).where(
            RecoveryCase.merchant_id == merchant_id
        )
    query = query.order_by(RecoveryAction.created_at.desc())
    rows = store._db.scalars(query).all()  # noqa: SLF001 — same-module store access
    return [_record_from_orm(row) for row in rows]
