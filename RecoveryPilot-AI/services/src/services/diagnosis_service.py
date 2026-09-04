"""Read-only diagnosis service: load snapshots, run the engine, never write.

Does not call Gemini, Razorpay, or the policy engine. Does not schedule retries.
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from database.models import Customer, Payment, RecoveryCase
from services.diagnosis.constants import (
    DEFAULT_TIMEZONE,
    SALARY_DEPENDENT_SEGMENTS,
)
from services.diagnosis.diagnosis_engine import diagnose
from services.diagnosis.models import (
    BatchDiagnosisResult,
    BatchDiagnosisSummary,
    CustomerSnapshot,
    DiagnosisContext,
    DiagnosisResult,
    OutageWindow,
    PaymentSnapshot,
    PromiseSnapshot,
    SubscriptionSnapshot,
)
from services.recovery_service import RecoveryCaseNotFoundError

logger = logging.getLogger(__name__)


class PaymentNotFoundError(Exception):
    """Raised when ``payment_id`` does not match a payments row."""

    def __init__(self, payment_id: UUID) -> None:
        self.payment_id = payment_id
        super().__init__(f"Payment not found: {payment_id}")


def _default_outage_path() -> Path:
    """simulator/output/outage_events.json relative to the repo root."""
    return Path(__file__).resolve().parents[3] / "simulator" / "output" / "outage_events.json"


def load_outage_windows(path: Path | None = None) -> list[OutageWindow]:
    """Load rail outages from JSON if the file exists.

    Args:
        path: Optional override. Defaults to simulator output.

    Returns:
        Parsed windows, or an empty list when the file is missing.
    """
    target = path or _default_outage_path()
    if not target.is_file():
        logger.info("diagnosis.outages.missing", extra={"path": str(target)})
        return []
    raw = json.loads(target.read_text(encoding="utf-8"))
    rows = raw if isinstance(raw, list) else raw.get("outages", [])
    windows: list[OutageWindow] = []
    for item in rows:
        windows.append(
            OutageWindow(
                rail=str(item.get("rail", "")),
                failure_reason=str(item.get("failure_reason", "")),
                started_at=datetime.fromisoformat(str(item["started_at"])),
                ended_at=datetime.fromisoformat(str(item["ended_at"])),
                institution=str(item.get("institution", "")),
                summary=str(item.get("summary", "")),
            )
        )
    logger.info("diagnosis.outages.loaded", extra={"count": len(windows)})
    return windows


def _payment_snapshot(row: Payment) -> PaymentSnapshot:
    """Map an ORM payment onto the engine snapshot. No secrets."""
    return PaymentSnapshot(
        id=row.id,
        amount=row.amount,
        currency=row.currency,
        status=row.payment_status,
        method=row.payment_method,
        failure_reason=row.failure_reason,
        attempt_number=row.attempt_number,
        created_at=row.created_at,
        paid_at=row.paid_at,
        due_date=row.payment_due_date,
        idempotency_key=row.idempotency_key,
        subscription_id=row.subscription_id,
        customer_id=row.customer_id,
    )


def _customer_snapshot(row: Customer) -> CustomerSnapshot:
    """Map an ORM customer. Salary overlay is inferred from segment."""
    return CustomerSnapshot(
        id=row.id,
        segment=row.customer_segment,
        salary_dependent=row.customer_segment.value in SALARY_DEPENDENT_SEGMENTS,
    )


def _subscription_snapshot(payment: Payment) -> SubscriptionSnapshot | None:
    """Map the payment's subscription when present."""
    sub = payment.subscription
    if sub is None:
        return None
    return SubscriptionSnapshot(
        id=sub.id,
        name=sub.subscription_name,
        billing_amount=sub.billing_amount,
        mandate_status=sub.mandate_status,
        subscription_status=sub.subscription_status,
        frequency=sub.billing_frequency,
    )


def _load_customer_payments(db: Session, customer_id: UUID) -> list[PaymentSnapshot]:
    """All ledger rows for the customer, used as behaviour history."""
    rows = db.scalars(
        select(Payment)
        .where(Payment.customer_id == customer_id)
        .order_by(Payment.created_at.asc())
    ).all()
    return [_payment_snapshot(row) for row in rows]


def _build_context(
    db: Session,
    payment: Payment,
    *,
    case: RecoveryCase | None,
    outages: list[OutageWindow],
    as_of: datetime | None,
) -> DiagnosisContext:
    """Assemble the engine context from already-loaded ORM rows."""
    promises: list[PromiseSnapshot] = []
    action_count = 0
    status = None
    if case is not None:
        status = case.recovery_status
        action_count = len(list(case.actions))
        promises = [
            PromiseSnapshot(status=row.promise_status, promised_date=row.promised_date)
            for row in case.promises
        ]
    return DiagnosisContext(
        as_of=as_of or datetime.now(UTC),
        timezone=DEFAULT_TIMEZONE,
        payment=_payment_snapshot(payment),
        customer=_customer_snapshot(payment.customer),
        subscription=_subscription_snapshot(payment),
        customer_payments=_load_customer_payments(db, payment.customer_id),
        outages=outages,
        promises=promises,
        recovery_action_count=action_count,
        recovery_status=status,
    )


def _load_payment(db: Session, payment_id: UUID) -> Payment:
    """Load a payment with customer and subscription, or raise."""
    payment = db.scalar(
        select(Payment)
        .options(selectinload(Payment.customer), selectinload(Payment.subscription))
        .where(Payment.id == payment_id)
    )
    if payment is None:
        raise PaymentNotFoundError(payment_id)
    return payment


def _load_case(db: Session, recovery_case_id: UUID) -> RecoveryCase:
    """Load a recovery case graph, or raise."""
    case = db.scalar(
        select(RecoveryCase)
        .options(
            selectinload(RecoveryCase.payment).selectinload(Payment.customer),
            selectinload(RecoveryCase.payment).selectinload(Payment.subscription),
            selectinload(RecoveryCase.actions),
            selectinload(RecoveryCase.promises),
        )
        .where(RecoveryCase.id == recovery_case_id)
    )
    if case is None:
        raise RecoveryCaseNotFoundError(recovery_case_id)
    return case


def diagnose_payment(
    db: Session,
    payment_id: UUID,
    *,
    outages: list[OutageWindow] | None = None,
    as_of: datetime | None = None,
) -> DiagnosisResult:
    """Diagnose one payment. Does not write diagnosis fields back to Postgres.

    Args:
        db: Request-scoped SQLAlchemy session (read only).
        payment_id: Ledger row to diagnose.
        outages: Optional injected windows; otherwise JSON file / empty.
        as_of: Clock used for overdue / payday features.

    Returns:
        Structured ``DiagnosisResult``.

    Raises:
        PaymentNotFoundError: When the payment does not exist.
    """
    logger.info("diagnosis.payment.start", extra={"payment_id": str(payment_id)})
    payment = _load_payment(db, payment_id)
    case = db.scalar(
        select(RecoveryCase)
        .options(selectinload(RecoveryCase.actions), selectinload(RecoveryCase.promises))
        .where(RecoveryCase.payment_id == payment_id)
    )
    windows = outages if outages is not None else load_outage_windows()
    context = _build_context(db, payment, case=case, outages=windows, as_of=as_of)
    result = diagnose(context)
    if case is not None:
        result = result.model_copy(update={"recovery_case_id": case.id})
    logger.info(
        "diagnosis.payment.ok",
        extra={"payment_id": str(payment_id), "diagnosis": result.diagnosis.value},
    )
    return result


def diagnose_case(
    db: Session,
    recovery_case_id: UUID,
    *,
    outages: list[OutageWindow] | None = None,
    as_of: datetime | None = None,
) -> DiagnosisResult:
    """Diagnose one recovery case from its failed payment.

    Args:
        db: Request-scoped SQLAlchemy session (read only).
        recovery_case_id: Case to diagnose.
        outages: Optional injected windows.
        as_of: Clock used for overdue / payday features.

    Returns:
        Structured ``DiagnosisResult``.

    Raises:
        RecoveryCaseNotFoundError: When the case does not exist.
    """
    logger.info(
        "diagnosis.case.start",
        extra={"recovery_case_id": str(recovery_case_id)},
    )
    case = _load_case(db, recovery_case_id)
    windows = outages if outages is not None else load_outage_windows()
    context = _build_context(db, case.payment, case=case, outages=windows, as_of=as_of)
    result = diagnose(context)
    result = result.model_copy(update={"recovery_case_id": case.id})
    logger.info(
        "diagnosis.case.ok",
        extra={
            "recovery_case_id": str(recovery_case_id),
            "diagnosis": result.diagnosis.value,
        },
    )
    return result


def summarize_results(results: list[DiagnosisResult]) -> BatchDiagnosisSummary:
    """Roll up diagnosis distribution, confidence, and priority bands.

    Args:
        results: Per-case engine outputs.

    Returns:
        Dashboard-oriented summary. Does not query the database.
    """
    diagnoses = Counter(item.diagnosis.value for item in results)
    buckets = Counter(item.priority_bucket.value for item in results)
    reasons = Counter()
    for item in results:
        reason = item.features.get("recorded_failure_reason") or item.diagnosis.value
        reasons[str(reason)] += 1
    avg = (
        round(sum(item.confidence for item in results) / len(results), 4) if results else 0.0
    )
    top = [
        {"reason": name, "count": count}
        for name, count in reasons.most_common(5)
    ]
    return BatchDiagnosisSummary(
        total_cases=len(results),
        diagnosed_cases=len(results),
        diagnosis_distribution=dict(diagnoses),
        average_confidence=avg,
        priority_distribution=dict(buckets),
        top_failure_reasons=top,
        unknown_diagnoses=diagnoses.get("UNKNOWN", 0),
    )


def diagnose_batch(
    db: Session,
    recovery_case_ids: list[UUID],
    *,
    outages: list[OutageWindow] | None = None,
    as_of: datetime | None = None,
) -> BatchDiagnosisResult:
    """Diagnose many recovery cases. Missing ids are reported, not raised.

    Args:
        db: Request-scoped SQLAlchemy session (read only).
        recovery_case_ids: Cases to diagnose.
        outages: Optional injected windows, shared across the batch.
        as_of: Clock used for overdue / payday features.

    Returns:
        Per-case results, missing ids, and an aggregate summary.
    """
    logger.info("diagnosis.batch.start", extra={"count": len(recovery_case_ids)})
    windows = outages if outages is not None else load_outage_windows()
    results: list[DiagnosisResult] = []
    missing: list[UUID] = []
    for case_id in recovery_case_ids:
        try:
            results.append(
                diagnose_case(db, case_id, outages=windows, as_of=as_of)
            )
        except RecoveryCaseNotFoundError:
            logger.info(
                "diagnosis.batch.missing",
                extra={"recovery_case_id": str(case_id)},
            )
            missing.append(case_id)
    summary = summarize_results(results)
    summary = summary.model_copy(
        update={"total_cases": len(recovery_case_ids)}
    )
    logger.info(
        "diagnosis.batch.ok",
        extra={
            "diagnosed": len(results),
            "missing": len(missing),
            "unknown": summary.unknown_diagnoses,
        },
    )
    return BatchDiagnosisResult(
        results=results,
        missing_case_ids=missing,
        summary=summary,
    )
