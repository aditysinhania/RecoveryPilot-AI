"""Read-only planner service: load snapshots, run the engine, never write.

Does not call Gemini, Razorpay, or a scheduler. Does not send messages
or execute retries.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from database.models import Payment, RecoveryCase
from services.diagnosis.constants import SALARY_DEPENDENT_SEGMENTS
from services.diagnosis.models import DiagnosisResult
from services.diagnosis_service import diagnose_case
from services.planner.constants import DEFAULT_TIMEZONE
from services.planner.models import (
    BatchPlannerResult,
    CustomerBehaviourSnapshot,
    MerchantPlannerSnapshot,
    PlannerContext,
    PlannerCustomerSnapshot,
    PlannerPair,
    RecoveryPlan,
)
from services.planner.planner_engine import plan, plan_batch_contexts, summarize_plans
from services.policy.models import PolicyDecisionResult
from services.policy_service import evaluate_case
from services.recovery_service import RecoveryCaseNotFoundError
from shared.enums import PromiseStatus, RecoveryActionType

logger = logging.getLogger(__name__)


def _default_behaviour_path() -> Path:
    """simulator/output/customer_behaviour.json relative to the repo root."""
    return Path(__file__).resolve().parents[3] / "simulator" / "output" / "customer_behaviour.json"


def load_behaviour(
    customer_id: UUID,
    *,
    path: Path | None = None,
) -> CustomerBehaviourSnapshot | None:
    """Load one customer behaviour row from JSON if the file exists.

    Args:
        customer_id: Customer to look up.
        path: Optional override. Defaults to simulator output.

    Returns:
        Snapshot or ``None`` when missing. Never imports the simulator package.
    """
    target = path or _default_behaviour_path()
    if not target.is_file():
        return None
    raw = json.loads(target.read_text(encoding="utf-8"))
    rows = raw.get("rows", []) if isinstance(raw, dict) else raw
    key = str(customer_id)
    for item in rows:
        if str(item.get("customer_id")) == key:
            return CustomerBehaviourSnapshot(
                previous_success_rate=float(item.get("observed_reliability", 0.5)),
                observed_reliability=float(item.get("observed_reliability", 0.5)),
                max_fail_streak=int(item.get("max_fail_streak", 0)),
                salary_dependent=bool(item.get("salary_dependent", False)),
            )
    return None


def _load_case(db: Session, recovery_case_id: UUID) -> RecoveryCase:
    """Load a recovery case graph, or raise."""
    case = db.scalar(
        select(RecoveryCase)
        .options(
            selectinload(RecoveryCase.payment).selectinload(Payment.customer),
            selectinload(RecoveryCase.payment).selectinload(Payment.subscription),
            selectinload(RecoveryCase.customer),
            selectinload(RecoveryCase.merchant),
            selectinload(RecoveryCase.actions),
            selectinload(RecoveryCase.promises),
        )
        .where(RecoveryCase.id == recovery_case_id)
    )
    if case is None:
        raise RecoveryCaseNotFoundError(recovery_case_id)
    return case


def _behaviour_from_diagnosis(
    diagnosis: DiagnosisResult,
    *,
    salary_dependent: bool,
) -> CustomerBehaviourSnapshot:
    """Fill behaviour from diagnosis features when JSON is absent."""
    rate = diagnosis.features.get("previous_success_rate")
    return CustomerBehaviourSnapshot(
        previous_success_rate=float(rate) if rate is not None else 0.5,
        observed_reliability=float(rate) if rate is not None else 0.5,
        salary_dependent=salary_dependent,
    )


def _build_context(
    case: RecoveryCase,
    diagnosis: DiagnosisResult,
    policy: PolicyDecisionResult,
    *,
    as_of: datetime | None,
) -> PlannerContext:
    """Assemble planner context from loaded ORM rows."""
    clock = as_of or datetime.now(UTC)
    customer = case.customer if case.customer is not None else case.payment.customer
    salary = customer.customer_segment.value in SALARY_DEPENDENT_SEGMENTS
    overlay = load_behaviour(customer.id)
    behaviour = overlay or _behaviour_from_diagnosis(diagnosis, salary_dependent=salary)
    merchant = case.merchant
    tz = merchant.timezone if merchant is not None else DEFAULT_TIMEZONE
    promised = None
    for row in case.promises:
        if row.promise_status == PromiseStatus.OPEN:
            if promised is None or row.promised_date > promised:
                promised = row.promised_date
    retries = sum(1 for row in case.actions if row.action_type == RecoveryActionType.RETRY_PAYMENT)
    age = 0
    sub = case.payment.subscription
    if sub is not None:
        age = max(0, (clock.date() - sub.created_at.date()).days)
    return PlannerContext(
        as_of=clock,
        diagnosis=diagnosis,
        policy=policy,
        customer=PlannerCustomerSnapshot(
            id=customer.id,
            segment=customer.customer_segment,
            salary_dependent=behaviour.salary_dependent or salary,
            timezone=tz,
        ),
        payment_amount=case.payment.amount,
        payment_method=case.payment.payment_method,
        behaviour=behaviour,
        merchant=MerchantPlannerSnapshot(
            name=merchant.merchant_name if merchant else "FitLife Gym",
            business_category=merchant.business_category if merchant else "Fitness & Wellness",
            timezone=tz,
        ),
        promised_date=promised,
        retry_count=retries,
        subscription_age_days=age,
        recovery_case_id=case.id,
        timezone=tz,
    )


def plan_case(
    db: Session,
    recovery_case_id: UUID,
    diagnosis: DiagnosisResult | None = None,
    policy: PolicyDecisionResult | None = None,
    *,
    as_of: datetime | None = None,
) -> RecoveryPlan:
    """Plan recovery for one case. Does not write or execute.

    Args:
        db: Request-scoped SQLAlchemy session (read only).
        recovery_case_id: Case to plan.
        diagnosis: Optional Phase 5A result.
        policy: Optional Phase 5B result.
        as_of: Evaluation clock.

    Returns:
        Structured ``RecoveryPlan``.

    Raises:
        RecoveryCaseNotFoundError: When the case does not exist.
    """
    logger.info("planner.case.start", extra={"recovery_case_id": str(recovery_case_id)})
    case = _load_case(db, recovery_case_id)
    resolved_diag = diagnosis or diagnose_case(db, recovery_case_id, as_of=as_of)
    resolved_diag = resolved_diag.model_copy(update={"recovery_case_id": case.id})
    resolved_policy = policy or evaluate_case(
        db, recovery_case_id, diagnosis=resolved_diag, as_of=as_of
    )
    context = _build_context(case, resolved_diag, resolved_policy, as_of=as_of)
    result = plan(context)
    logger.info(
        "planner.case.ok",
        extra={
            "recovery_case_id": str(recovery_case_id),
            "strategy": result.strategy.value,
        },
    )
    return result


def plan_batch(
    db: Session,
    items: list[PlannerPair],
    *,
    as_of: datetime | None = None,
) -> BatchPlannerResult:
    """Plan many diagnosis+policy pairs. Missing cases are reported, not raised.

    Args:
        db: Request-scoped SQLAlchemy session (read only).
        items: Diagnosis and policy results, typically with ``recovery_case_id``.
        as_of: Shared evaluation clock.

    Returns:
        Per-case plans, missing ids, and an aggregate summary.
    """
    logger.info("planner.batch.start", extra={"count": len(items)})
    contexts: list[PlannerContext] = []
    missing: list[UUID] = []
    for item in items:
        case_id = item.diagnosis.recovery_case_id or item.policy.recovery_case_id
        if case_id is None:
            logger.info(
                "planner.batch.skip_no_case",
                extra={"payment_id": str(item.diagnosis.payment_id)},
            )
            continue
        try:
            case = _load_case(db, case_id)
        except RecoveryCaseNotFoundError:
            logger.info("planner.batch.missing", extra={"recovery_case_id": str(case_id)})
            missing.append(case_id)
            continue
        contexts.append(_build_context(case, item.diagnosis, item.policy, as_of=as_of))
    batch = plan_batch_contexts(contexts, missing_case_ids=missing)
    logger.info(
        "planner.batch.ok",
        extra={"planned": len(batch.results), "missing": len(missing)},
    )
    return batch


__all__ = [
    "plan_batch",
    "plan_case",
    "summarize_plans",
]
