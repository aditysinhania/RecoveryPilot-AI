"""Read-only policy service: load snapshots, run the engine, never write.

Does not call Gemini, Razorpay, or the planner. Does not schedule retries
or generate payment links.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from database.models import Customer, Payment, RecoveryAction, RecoveryCase
from services.diagnosis.models import DiagnosisResult
from services.diagnosis_service import diagnose_case
from services.policy.constants import DEFAULT_TIMEZONE, POLICY_VERSION
from services.policy.models import (
    BatchPolicyResult,
    CommunicationSnapshot,
    CustomerPolicySnapshot,
    PaymentPolicySnapshot,
    PolicyContext,
    PolicyDecisionResult,
    PromisePolicySnapshot,
    RecoveryActionSnapshot,
    SubscriptionPolicySnapshot,
)
from services.policy.policy_engine import (
    evaluate,
    evaluate_batch_contexts,
    summarize_decisions,
)
from services.recovery_service import RecoveryCaseNotFoundError
from shared.enums import ConsentStatus

logger = logging.getLogger(__name__)


def _consent_granted(status: ConsentStatus) -> bool:
    """Postgres stores only the umbrella consent enum, not per-channel flags."""
    return status == ConsentStatus.GRANTED


def _customer_snapshot(row: Customer) -> CustomerPolicySnapshot:
    """Map an ORM customer. Per-channel flags follow the umbrella consent status."""
    granted = _consent_granted(row.consent_status)
    return CustomerPolicySnapshot(
        id=row.id,
        segment=row.customer_segment,
        consent_status=row.consent_status,
        consent_whatsapp=granted,
        consent_sms=granted,
        consent_voice=granted,
        consent_email=granted,
        hardship=False,
        timezone=DEFAULT_TIMEZONE,
    )


def _payment_snapshot(row: Payment) -> PaymentPolicySnapshot:
    """Map an ORM payment. No secrets."""
    return PaymentPolicySnapshot(
        id=row.id,
        amount=row.amount,
        status=row.payment_status,
        created_at=row.created_at,
        attempt_number=row.attempt_number,
    )


def _subscription_snapshot(payment: Payment) -> SubscriptionPolicySnapshot | None:
    """Map the payment's subscription when present."""
    sub = payment.subscription
    if sub is None:
        return None
    return SubscriptionPolicySnapshot(
        id=sub.id,
        mandate_status=sub.mandate_status,
        subscription_status=sub.subscription_status,
    )


def _action_snapshot(row: RecoveryAction) -> RecoveryActionSnapshot:
    """Map one recovery action, including optional channel metadata."""
    meta = row.action_metadata or {}
    channel = meta.get("channel")
    return RecoveryActionSnapshot(
        action_type=row.action_type,
        execution_status=row.execution_status,
        scheduled_time=row.scheduled_time,
        executed_time=row.executed_time,
        created_at=row.created_at,
        retry_number=row.retry_number,
        channel=str(channel) if channel else None,
    )


def _communications(actions: list[RecoveryActionSnapshot]) -> list[CommunicationSnapshot]:
    """Derive communication history from action metadata when a channel is set."""
    rows: list[CommunicationSnapshot] = []
    for action in actions:
        if action.channel:
            rows.append(
                CommunicationSnapshot(channel=action.channel, sent_at=action.event_time())
            )
    return rows


def _load_case(db: Session, recovery_case_id: UUID) -> RecoveryCase:
    """Load a recovery case graph, or raise."""
    case = db.scalar(
        select(RecoveryCase)
        .options(
            selectinload(RecoveryCase.payment).selectinload(Payment.customer),
            selectinload(RecoveryCase.payment).selectinload(Payment.subscription),
            selectinload(RecoveryCase.customer),
            selectinload(RecoveryCase.actions),
            selectinload(RecoveryCase.promises),
        )
        .where(RecoveryCase.id == recovery_case_id)
    )
    if case is None:
        raise RecoveryCaseNotFoundError(recovery_case_id)
    return case


def _build_context(
    case: RecoveryCase,
    diagnosis: DiagnosisResult,
    *,
    as_of: datetime | None,
) -> PolicyContext:
    """Assemble the engine context from already-loaded ORM rows."""
    actions = [_action_snapshot(row) for row in case.actions]
    customer = case.customer if case.customer is not None else case.payment.customer
    return PolicyContext(
        as_of=as_of or datetime.now(UTC),
        diagnosis=diagnosis,
        customer=_customer_snapshot(customer),
        payment=_payment_snapshot(case.payment),
        subscription=_subscription_snapshot(case.payment),
        recovery_actions=actions,
        promises=[
            PromisePolicySnapshot(
                status=row.promise_status,
                promised_date=row.promised_date,
                promised_amount=row.promised_amount,
            )
            for row in case.promises
        ],
        communications=_communications(actions),
        recovery_case_id=case.id,
        recovery_status=case.recovery_status,
    )


def evaluate_case(
    db: Session,
    recovery_case_id: UUID,
    diagnosis: DiagnosisResult | None = None,
    *,
    as_of: datetime | None = None,
) -> PolicyDecisionResult:
    """Evaluate policy for one recovery case. Does not write policy fields.

    Args:
        db: Request-scoped SQLAlchemy session (read only).
        recovery_case_id: Case to evaluate.
        diagnosis: Optional Phase 5A result. Loaded via ``diagnose_case`` when omitted.
        as_of: Evaluation clock.

    Returns:
        Structured ``PolicyDecisionResult``.

    Raises:
        RecoveryCaseNotFoundError: When the case does not exist.
    """
    logger.info(
        "policy.case.start",
        extra={"recovery_case_id": str(recovery_case_id)},
    )
    case = _load_case(db, recovery_case_id)
    resolved = diagnosis or diagnose_case(db, recovery_case_id, as_of=as_of)
    resolved = resolved.model_copy(update={"recovery_case_id": case.id})
    context = _build_context(case, resolved, as_of=as_of)
    result = evaluate(context)
    logger.info(
        "policy.case.ok",
        extra={
            "recovery_case_id": str(recovery_case_id),
            "decision": result.decision.value,
            "policy_name": result.policy_name,
            "policy_version": POLICY_VERSION,
        },
    )
    return result


def evaluate_batch(
    db: Session,
    diagnoses: list[DiagnosisResult],
    *,
    as_of: datetime | None = None,
) -> BatchPolicyResult:
    """Evaluate policy for many diagnoses. Missing cases are reported, not raised.

    Args:
        db: Request-scoped SQLAlchemy session (read only).
        diagnoses: Phase 5A results, typically with ``recovery_case_id`` set.
        as_of: Shared evaluation clock.

    Returns:
        Per-case decisions, missing ids, and an aggregate summary.
    """
    logger.info("policy.batch.start", extra={"count": len(diagnoses)})
    contexts: list[PolicyContext] = []
    missing: list[UUID] = []
    for item in diagnoses:
        case_id = item.recovery_case_id
        if case_id is None:
            logger.info("policy.batch.skip_no_case", extra={"payment_id": str(item.payment_id)})
            continue
        try:
            case = _load_case(db, case_id)
        except RecoveryCaseNotFoundError:
            logger.info(
                "policy.batch.missing",
                extra={"recovery_case_id": str(case_id)},
            )
            missing.append(case_id)
            continue
        contexts.append(_build_context(case, item, as_of=as_of))
    batch = evaluate_batch_contexts(contexts, missing_case_ids=missing)
    logger.info(
        "policy.batch.ok",
        extra={
            "evaluated": len(batch.results),
            "missing": len(missing),
            "stopped": batch.summary.stopped_cases,
        },
    )
    return batch


__all__ = [
    "evaluate_batch",
    "evaluate_case",
    "summarize_decisions",
]
