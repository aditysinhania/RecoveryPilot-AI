"""Execute RecoveryPlans against Razorpay Sandbox with policy gates and mock comms."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from services.action_orchestrator.constants import (
    ACTOR_NAME,
    DISPLAY_CANCELLED,
    DISPLAY_FAILED,
    DISPLAY_RETRYING,
    DISPLAY_SCHEDULED,
    DISPLAY_SENT,
    DISPLAY_SUCCESS,
    ORCHESTRATOR_VERSION,
    TERMINAL_DISPLAY,
)
from services.action_orchestrator.gates import evaluate_gates
from services.action_orchestrator.mapping import (
    action_chip_for,
    action_type_for,
    db_status_for,
    display_status_for,
)
from services.action_orchestrator.models import (
    ActionExecutionResult,
    ActionRecord,
    GateDecision,
    OrchestratorContext,
)
from services.action_orchestrator.persistence import ActionStore
from services.communications.models import DeliveryResult
from services.communications.router import CommunicationRouter
from services.executor.idempotency import execution_id_for, make_idempotency_key
from services.planner.models import PlannerStrategy
from services.policy.models import PolicyDecision
from services.razorpay_actions.constants import WAIT_STRATEGIES
from services.razorpay_actions.errors import (
    RazorpayActionPermanentError,
    RazorpayActionTransientError,
)
from services.razorpay_actions.models import RazorpayActionRequest, RazorpayActionResult
from services.razorpay_actions.service import RazorpayActionService
from services.scheduler.backoff import next_backoff
from services.scheduler.service import ActionScheduler
from shared.enums import AuditEventType, PolicyDecision as AuditPolicyDecision

logger = logging.getLogger(__name__)

_AUDIT_POLICY = {
    PolicyDecision.ALLOW: AuditPolicyDecision.ALLOW,
    PolicyDecision.WAIT: AuditPolicyDecision.ALLOW,
    PolicyDecision.DENY: AuditPolicyDecision.BLOCK,
    PolicyDecision.STOP: AuditPolicyDecision.BLOCK,
    PolicyDecision.ESCALATE: AuditPolicyDecision.ESCALATE,
}


class ActionNotFoundError(Exception):
    """Raised when replay cannot find an execution_id."""

    def __init__(self, execution_id: UUID) -> None:
        self.execution_id = execution_id
        super().__init__(f"Action execution not found: {execution_id}")


def _mask_contact(value: str) -> str:
    """Keep a short suffix for audit payloads. Never log the full phone/email."""
    trimmed = (value or "").strip()
    if "@" in trimmed:
        name, _, domain = trimmed.partition("@")
        return f"{name[:1]}***@{domain}" if domain else "***"
    digits = "".join(ch for ch in trimmed if ch.isdigit())
    if len(digits) >= 4:
        return f"***{digits[-4:]}"
    return "***"


def _audit_policy(decision: PolicyDecision) -> AuditPolicyDecision:
    """Map engine PolicyDecision onto the audit-log PG enum."""
    return _AUDIT_POLICY.get(decision, AuditPolicyDecision.ALLOW)


def _result_from_record(
    record: ActionRecord,
    *,
    request_id: str,
    correlation_id: str,
    replayed: bool = False,
    deliveries: list[DeliveryResult] | None = None,
) -> ActionExecutionResult:
    """Build the public result from a stored action row."""
    meta = record.action_metadata or {}
    display = display_status_for(meta, record.execution_status)
    strategy = str(meta.get("planner_strategy") or record.action_type.value)
    return ActionExecutionResult(
        execution_id=record.id,
        recovery_case_id=record.recovery_case_id,
        idempotency_key=str(meta.get("idempotency_key") or ""),
        planner_strategy=strategy,
        action_type=record.action_type.value,
        display_status=display,
        execution_status=record.execution_status.value,
        action_chip=action_chip_for(display, record.action_type, payment_link=record.razorpay_payment_link),
        scheduled_time=record.scheduled_time,
        executed_time=record.executed_time,
        retry_attempts=record.retry_number,
        payment_link=record.razorpay_payment_link,
        delivery_status=str(meta.get("delivery_status") or "") or None,
        deliveries=deliveries or [],
        request_id=str(meta.get("request_id") or request_id),
        correlation_id=str(meta.get("correlation_id") or correlation_id),
        replayed=replayed,
        dead_lettered=bool(meta.get("dead_lettered")),
        policy_reason=str(meta.get("policy_reason") or "") or None,
        razorpay_resource_id=str(meta.get("razorpay_resource_id") or "") or None,
        metadata=meta,
    )


class ActionOrchestrator:
    """Production-style executor for RecoveryPlans. Does not change planner/policy."""

    def __init__(
        self,
        store: ActionStore,
        razorpay: RazorpayActionService,
        comms: CommunicationRouter,
        scheduler: ActionScheduler,
    ) -> None:
        self._store = store
        self._razorpay = razorpay
        self._comms = comms
        self._scheduler = scheduler

    def run(
        self,
        context: OrchestratorContext,
        *,
        force_schedule: bool = False,
        replay: bool = False,
    ) -> ActionExecutionResult:
        """Execute or schedule one plan. Idempotent on case+strategy+scheduled_at.

        Args:
            context: Plan, policy, customer, payment, and correlation ids.
            force_schedule: Persist SCHEDULED without calling Razorpay.
            replay: Re-run outbound work for webhook/idempotent replay.

        Returns:
            Structured execution result with display status and delivery.
        """
        plan = context.plan
        case_id = plan.recovery_case_id
        if case_id is None:
            raise ValueError("RecoveryPlan.recovery_case_id is required")
        key = make_idempotency_key(case_id, plan.strategy.value, plan.scheduled_at)
        execution_id = execution_id_for(key)
        existing = self._store.get(execution_id) or self._store.get_by_idempotency(key)
        if existing is not None:
            display = display_status_for(existing.action_metadata, existing.execution_status)
            if display in TERMINAL_DISPLAY or (not replay and display == DISPLAY_SENT):
                logger.info(
                    "orchestrator.idempotent.hit",
                    extra={"execution_id": str(existing.id), "recovery_case_id": str(case_id)},
                )
                return _result_from_record(
                    existing,
                    request_id=context.request_id,
                    correlation_id=context.correlation_id,
                    replayed=True,
                )
        gate = evaluate_gates(plan, context.policy, as_of=context.as_of, force_schedule=force_schedule)
        record = existing or ActionRecord(
            id=execution_id,
            recovery_case_id=case_id,
            action_type=action_type_for(plan.strategy),
            scheduled_time=plan.scheduled_at,
            retry_number=existing.retry_number if existing else 0,
            action_metadata={},
        )
        record.action_metadata = self._base_metadata(context, key, execution_id, gate)
        if gate.block:
            return self._finalize(
                record,
                context,
                display=DISPLAY_CANCELLED,
                event=AuditEventType.ACTION_SKIPPED,
                summary=f"Policy blocked {plan.strategy.value}",
                extra={"policy_reason": gate.reason},
            )
        if gate.defer and not replay:
            run_at = gate.run_at or plan.scheduled_at
            record.scheduled_time = run_at
            record.action_metadata["display_status"] = DISPLAY_SCHEDULED
            stored = self._persist_status(record, DISPLAY_SCHEDULED)
            self._scheduler.schedule(
                execution_id=stored.id,
                recovery_case_id=case_id,
                run_at=run_at,
                reason=gate.reason,
                attempt=stored.retry_number,
            )
            self._audit(
                context,
                AuditEventType.ACTION_SCHEDULED,
                f"Scheduled {plan.strategy.value} for {run_at.isoformat()}",
                stored,
            )
            logger.info(
                "orchestrator.scheduled",
                extra={"execution_id": str(stored.id), "recovery_case_id": str(case_id)},
            )
            return _result_from_record(
                stored, request_id=context.request_id, correlation_id=context.correlation_id
            )
        return self._dispatch(record, context, key)

    def replay(self, execution_id: UUID, context: OrchestratorContext) -> ActionExecutionResult:
        """Replay one execution using the original idempotency key.

        Args:
            execution_id: Recovery action / execution id.
            context: Fresh plan/policy snapshots plus request correlation.

        Returns:
            The same result on success; a new attempt on transient failure.

        Raises:
            ActionNotFoundError: Unknown execution_id.
        """
        record = self._store.get(execution_id)
        if record is None:
            raise ActionNotFoundError(execution_id)
        logger.info(
            "orchestrator.replay.start",
            extra={"execution_id": str(execution_id), "recovery_case_id": str(record.recovery_case_id)},
        )
        return self.run(context, replay=True)

    def run_due(self, record: ActionRecord, context: OrchestratorContext) -> ActionExecutionResult:
        """Execute a previously scheduled row when the clock reaches scheduled_time."""
        meta = dict(record.action_metadata)
        strategy_value = str(meta.get("planner_strategy") or context.plan.strategy.value)
        try:
            strategy = PlannerStrategy(strategy_value)
        except ValueError:
            strategy = context.plan.strategy
        if strategy in WAIT_STRATEGIES and context.as_of >= (record.scheduled_time or context.as_of):
            record.executed_time = context.as_of
            record.action_metadata["display_status"] = DISPLAY_SUCCESS
            self._persist_status(record, DISPLAY_SUCCESS)
            self._scheduler.complete(record.id)
            fallback = context.plan.fallback_strategy
            if fallback not in WAIT_STRATEGIES and fallback != strategy:
                plan = context.plan.model_copy(update={"strategy": fallback, "scheduled_at": context.as_of})
                due_context = context.model_copy(update={"plan": plan})
                logger.info(
                    "orchestrator.due.fallback",
                    extra={
                        "execution_id": str(record.id),
                        "fallback": fallback.value,
                        "recovery_case_id": str(record.recovery_case_id),
                    },
                )
                return self.run(due_context)
            return _result_from_record(
                record, request_id=context.request_id, correlation_id=context.correlation_id
            )
        return self.run(context, replay=True)

    def _dispatch(
        self,
        record: ActionRecord,
        context: OrchestratorContext,
        key: str,
    ) -> ActionExecutionResult:
        """Call Razorpay + comms, then persist SENT → SUCCESS / FAILED."""
        plan = context.plan
        record.action_metadata["display_status"] = DISPLAY_SENT
        record.executed_time = context.as_of
        stored = self._persist_status(record, DISPLAY_SENT)
        rzp: RazorpayActionResult | None = None
        try:
            if plan.strategy == PlannerStrategy.STOP_RECOVERY:
                return self._finalize(
                    stored,
                    context,
                    display=DISPLAY_CANCELLED,
                    event=AuditEventType.ACTION_SKIPPED,
                    summary="Stop recovery — no Razorpay call",
                )
            if plan.strategy == PlannerStrategy.ESCALATE_TO_HUMAN:
                return self._finalize(
                    stored,
                    context,
                    display=DISPLAY_SUCCESS,
                    event=AuditEventType.ACTION_EXECUTED,
                    summary="Escalated to human — no Razorpay call",
                )
            if plan.strategy in WAIT_STRATEGIES:
                fallback = plan.fallback_strategy
                if fallback not in WAIT_STRATEGIES and fallback != plan.strategy:
                    nested = context.model_copy(
                        update={
                            "plan": plan.model_copy(
                                update={"strategy": fallback, "scheduled_at": context.as_of}
                            )
                        }
                    )
                    stored.action_metadata["display_status"] = DISPLAY_SUCCESS
                    self._persist_status(stored, DISPLAY_SUCCESS)
                    self._scheduler.complete(stored.id)
                    return self.run(nested)
                return self._finalize(
                    stored,
                    context,
                    display=DISPLAY_SUCCESS,
                    event=AuditEventType.ACTION_EXECUTED,
                    summary=f"{plan.strategy.value} window reached",
                )
            request = RazorpayActionRequest(
                recovery_case_id=stored.recovery_case_id,
                payment_id=context.payment.id,
                amount=context.payment.amount,
                currency=context.payment.currency,
                customer_name=context.customer.full_name,
                customer_email=context.customer.email,
                customer_phone=context.customer.phone,
                description=f"{context.merchant_name} recovery",
                idempotency_key=key,
                notes={"strategy": plan.strategy.value},
            )
            rzp = self._razorpay.execute_strategy(plan.strategy, request, as_of=context.as_of)
        except RazorpayActionTransientError as exc:
            logger.info(
                "orchestrator.razorpay.transient",
                extra={"execution_id": str(stored.id), "recovery_case_id": str(stored.recovery_case_id)},
            )
            return self._backoff_or_dead_letter(stored, context, str(exc))
        except RazorpayActionPermanentError as exc:
            logger.info(
                "orchestrator.razorpay.permanent",
                extra={"execution_id": str(stored.id), "recovery_case_id": str(stored.recovery_case_id)},
            )
            return self._finalize(
                stored,
                context,
                display=DISPLAY_FAILED,
                event=AuditEventType.ACTION_EXECUTED,
                summary="Razorpay Sandbox rejected the request",
                extra={"error": str(exc)},
                response_code="RAZORPAY_PERMANENT",
                response_message=str(exc)[:512],
            )

        payment_link = None
        resource_id = None
        if rzp is not None:
            payment_link = rzp.short_url
            resource_id = rzp.resource_id
            stored.razorpay_payment_link = payment_link
            stored.action_metadata["razorpay_resource_id"] = resource_id
            stored.action_metadata["razorpay_kind"] = rzp.kind
            stored.action_metadata["razorpay_status"] = rzp.status
            stored.action_metadata["razorpay_mock"] = rzp.mock

        silent = plan.strategy == PlannerStrategy.RETRY_SILENTLY
        deliveries = self._deliver(stored, context, key, payment_link=payment_link, silent=silent)
        delivery_status = deliveries[0].status if deliveries else "SKIPPED"
        stored.action_metadata["delivery_status"] = delivery_status
        stored.action_metadata["deliveries"] = [item.model_dump(mode="json") for item in deliveries]
        display = DISPLAY_SUCCESS
        if delivery_status == "FAILED" and not silent:
            return self._backoff_or_dead_letter(stored, context, "communication_failed")
        result = self._finalize(
            stored,
            context,
            display=display,
            event=AuditEventType.ACTION_EXECUTED,
            summary=f"Executed {plan.strategy.value}",
            extra={"razorpay_resource_id": resource_id, "delivery_status": delivery_status},
            deliveries=deliveries,
            response_code="OK",
            response_message="sandbox_ok",
        )
        self._scheduler.complete(stored.id)
        return result

    def _deliver(
        self,
        record: ActionRecord,
        context: OrchestratorContext,
        key: str,
        *,
        payment_link: str | None,
        silent: bool,
    ) -> list[DeliveryResult]:
        """Send one sandbox communication if policy and consent allow it."""
        plan = context.plan
        link_line = f" Pay: {payment_link}" if payment_link else ""
        body = f"{context.merchant_name}: complete your pending payment.{link_line}"
        return self._comms.deliver(
            recovery_case_id=record.recovery_case_id,
            merchant_id=context.customer.merchant_id,
            recommended=list(plan.recommended_channels),
            allowed=list(context.policy.allowed_channels),
            blocked=list(context.policy.blocked_channels),
            silent=silent,
            consent_granted=context.customer.consent_granted,
            contact_by_channel={
                "WhatsApp": _mask_contact(context.customer.phone),
                "SMS": _mask_contact(context.customer.phone),
                "Email": _mask_contact(context.customer.email),
            },
            template="recovery_action_v1",
            body=body,
            idempotency_key=key,
            request_id=context.request_id,
            correlation_id=context.correlation_id,
        )

    def _backoff_or_dead_letter(
        self,
        record: ActionRecord,
        context: OrchestratorContext,
        error: str,
    ) -> ActionExecutionResult:
        """Schedule exponential backoff or dead-letter after the retry cap."""
        delay = next_backoff(record.retry_number)
        record.retry_number += 1
        record.response_code = "TRANSIENT"
        record.response_message = error[:512]
        if delay is None:
            record.action_metadata["dead_lettered"] = True
            record.action_metadata["display_status"] = DISPLAY_FAILED
            stored = self._persist_status(record, DISPLAY_FAILED)
            self._scheduler.complete(stored.id, status="dead_letter")
            self._audit(
                context,
                AuditEventType.ACTION_EXECUTED,
                "Dead-lettered after retry limit",
                stored,
            )
            logger.info(
                "orchestrator.dead_letter",
                extra={"execution_id": str(stored.id), "recovery_case_id": str(stored.recovery_case_id)},
            )
            return _result_from_record(
                stored, request_id=context.request_id, correlation_id=context.correlation_id
            )
        run_at = context.as_of + delay
        record.scheduled_time = run_at
        record.executed_time = None
        record.action_metadata["display_status"] = DISPLAY_RETRYING
        record.action_metadata["retrying"] = True
        stored = self._persist_status(record, DISPLAY_RETRYING)
        self._scheduler.schedule(
            execution_id=stored.id,
            recovery_case_id=stored.recovery_case_id,
            run_at=run_at,
            reason="BACKOFF",
            attempt=stored.retry_number,
        )
        self._audit(
            context,
            AuditEventType.ACTION_SCHEDULED,
            f"Retry scheduled after transient failure in {delay}",
            stored,
        )
        logger.info(
            "orchestrator.backoff",
            extra={
                "execution_id": str(stored.id),
                "retry_number": stored.retry_number,
                "recovery_case_id": str(stored.recovery_case_id),
            },
        )
        return _result_from_record(
            stored, request_id=context.request_id, correlation_id=context.correlation_id
        )

    def _base_metadata(
        self,
        context: OrchestratorContext,
        key: str,
        execution_id: UUID,
        gate: GateDecision,
    ) -> dict[str, Any]:
        """JSON stored on recovery_actions.metadata. No secrets."""
        plan = context.plan
        return {
            "idempotency_key": key,
            "execution_id": str(execution_id),
            "planner_strategy": plan.strategy.value,
            "fallback_strategy": plan.fallback_strategy.value,
            "orchestrator_version": ORCHESTRATOR_VERSION,
            "request_id": context.request_id,
            "correlation_id": context.correlation_id,
            "blocked_channels": gate.blocked_channels,
            "allowed_channels": list(context.policy.allowed_channels),
            "policy_reason": gate.reason,
            "policy_decision": context.policy.decision.value,
        }

    def _persist_status(self, record: ActionRecord, display: str) -> ActionRecord:
        """Write execution_status from the display lifecycle."""
        record.action_metadata["display_status"] = display
        record.execution_status = db_status_for(display)
        return self._store.save(record)

    def _finalize(
        self,
        record: ActionRecord,
        context: OrchestratorContext,
        *,
        display: str,
        event: AuditEventType,
        summary: str,
        extra: dict[str, Any] | None = None,
        deliveries: list[DeliveryResult] | None = None,
        response_code: str | None = None,
        response_message: str | None = None,
    ) -> ActionExecutionResult:
        """Persist a terminal or skip status and append audit."""
        if extra:
            record.action_metadata.update({k: v for k, v in extra.items() if v is not None})
        if response_code:
            record.response_code = response_code
        if response_message:
            record.response_message = response_message
        if display in {DISPLAY_SUCCESS, DISPLAY_FAILED, DISPLAY_CANCELLED} and record.executed_time is None:
            record.executed_time = context.as_of
        stored = self._persist_status(record, display)
        if display in {DISPLAY_SUCCESS, DISPLAY_FAILED, DISPLAY_CANCELLED}:
            self._scheduler.complete(stored.id)
        self._audit(context, event, summary, stored)
        logger.info(
            "orchestrator.finalize",
            extra={
                "execution_id": str(stored.id),
                "display_status": display,
                "recovery_case_id": str(stored.recovery_case_id),
            },
        )
        return _result_from_record(
            stored,
            request_id=context.request_id,
            correlation_id=context.correlation_id,
            deliveries=deliveries,
        )

    def _audit(
        self,
        context: OrchestratorContext,
        event_type: AuditEventType,
        summary: str,
        record: ActionRecord,
    ) -> None:
        """Append one audit_logs row with request_id and correlation_id."""
        payload = {
            "request_id": context.request_id,
            "correlation_id": context.correlation_id,
            "idempotency_key": record.action_metadata.get("idempotency_key"),
            "execution_id": str(record.id),
            "planner_strategy": record.action_metadata.get("planner_strategy"),
            "display_status": record.action_metadata.get("display_status"),
            "razorpay_resource_id": record.action_metadata.get("razorpay_resource_id"),
            "delivery_status": record.action_metadata.get("delivery_status"),
            "orchestrator_version": ORCHESTRATOR_VERSION,
            "actor": ACTOR_NAME,
        }
        self._store.append_audit(
            recovery_case_id=record.recovery_case_id,
            event_type=event_type,
            summary=summary,
            payload=payload,
            policy_decision=_audit_policy(context.policy.decision),
            actor_name=ACTOR_NAME,
        )

    def apply_provider_webhook(
        self,
        *,
        recovery_case_id: UUID,
        provider_event: str,
        razorpay_event_id: str,
        request_id: str,
        correlation_id: str,
        as_of: datetime,
        extra: dict[str, Any] | None = None,
        replay: bool = False,
    ) -> ActionRecord | None:
        """Apply a live Razorpay webhook onto the latest action and audit trail.

        Does not re-run planner, policy, or diagnosis. Recovery case status is
        updated by ``razorpay_webhooks.apply`` via this same service path.

        Args:
            recovery_case_id: Mapped case.
            provider_event: Razorpay event name.
            razorpay_event_id: Provider event id.
            request_id: HTTP request id.
            correlation_id: Workflow correlation id.
            as_of: Webhook clock.
            extra: Extra audit payload (never secrets).
            replay: Duplicate delivery; append WEBHOOK_REPLAY and return.

        Returns:
            The latest action row when one exists.
        """
        from services.razorpay_webhooks.constants import (
            CAPTURE_EVENTS,
            DISPLAY_WEBHOOK_REPLAY,
            EVENT_PAYMENT_AUTHORIZED,
            EVENT_PAYMENT_FAILED,
            STOP_EVENTS,
            WEBHOOK_ACTOR,
        )

        history = self._store.list_for_case(recovery_case_id)
        record = history[0] if history else None
        if replay:
            payload = {
                "request_id": request_id,
                "correlation_id": correlation_id,
                "razorpay_event_id": razorpay_event_id,
                "event": provider_event,
                "display_type": DISPLAY_WEBHOOK_REPLAY,
                "replay": True,
                "webhook_replay": True,
                "duplicate": True,
                **(extra or {}),
            }
            self._store.append_audit(
                recovery_case_id=recovery_case_id,
                event_type=AuditEventType.ACTION_EXECUTED,
                summary="Webhook replay ignored (duplicate event id)",
                payload=payload,
                actor_name=WEBHOOK_ACTOR,
            )
            logger.info(
                "orchestrator.webhook.replay",
                extra={"recovery_case_id": str(recovery_case_id), "razorpay_event_id": razorpay_event_id},
            )
            return record
        from services.razorpay_webhooks.apply import apply_recovery_status

        apply_recovery_status(
            getattr(self._store, "_db", None),
            recovery_case_id,
            provider_event,
            as_of=as_of,
        )
        if provider_event in CAPTURE_EVENTS:
            display = DISPLAY_SUCCESS
            audit_type = AuditEventType.PAYMENT_CAPTURED
            summary = f"Razorpay {provider_event} captured payment"
        elif provider_event in STOP_EVENTS:
            display = DISPLAY_CANCELLED
            audit_type = AuditEventType.RECOVERY_STOPPED
            summary = f"Razorpay {provider_event} stopped recovery"
        elif provider_event == EVENT_PAYMENT_FAILED:
            display = DISPLAY_FAILED
            audit_type = AuditEventType.ACTION_EXECUTED
            summary = "Razorpay payment.failed"
        elif provider_event == EVENT_PAYMENT_AUTHORIZED:
            display = DISPLAY_SENT
            audit_type = AuditEventType.ACTION_EXECUTED
            summary = "Razorpay payment.authorized"
        else:
            display = DISPLAY_SENT
            audit_type = AuditEventType.ACTION_EXECUTED
            summary = f"Razorpay {provider_event}"

        if record is not None:
            record.action_metadata["webhook_event"] = provider_event
            record.action_metadata["webhook_event_id"] = razorpay_event_id
            record.action_metadata["display_status"] = display
            if display == DISPLAY_SUCCESS:
                record.executed_time = record.executed_time or as_of
                self._scheduler.complete(record.id)
            stored = self._persist_status(record, display)
        else:
            stored = None
        payload = {
            "request_id": request_id,
            "correlation_id": correlation_id,
            "razorpay_event_id": razorpay_event_id,
            "event": provider_event,
            "execution_id": str(stored.id) if stored is not None else None,
            **(extra or {}),
        }
        self._store.append_audit(
            recovery_case_id=recovery_case_id,
            event_type=audit_type,
            summary=summary,
            payload=payload,
            actor_name=WEBHOOK_ACTOR,
        )
        logger.info(
            "orchestrator.webhook.apply",
            extra={
                "recovery_case_id": str(recovery_case_id),
                "event": provider_event,
                "razorpay_event_id": razorpay_event_id,
            },
        )
        return stored
