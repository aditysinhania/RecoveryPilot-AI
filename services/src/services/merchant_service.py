"""Read-only merchant dashboard queries.

Routers must not run SQL. This module is the only place that loads merchant
ledger data for the dashboard. No AI, Razorpay, or recovery execution.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database.models import (
    Customer,
    Merchant,
    MerchantMetric,
    Payment,
    PaymentStatus,
    RecoveryCase,
    RecoveryStatus,
    Subscription,
)

logger = logging.getLogger(__name__)


class MerchantNotFoundError(Exception):
    """Raised when ``merchant_id`` does not match a merchants row."""

    def __init__(self, merchant_id: UUID) -> None:
        self.merchant_id = merchant_id
        super().__init__(f"Merchant not found: {merchant_id}")


@dataclass(frozen=True)
class MerchantSummaryResult:
    """Merchant row plus live counts and an optional metrics snapshot."""

    merchant: Merchant
    customers: int
    subscriptions: int
    payments: int
    failed_payments: int
    recovery_cases: int
    metrics: MerchantMetric | None


@dataclass(frozen=True)
class PaymentPageResult:
    """One page of payment rows and the unfiltered total."""

    items: list[Payment]
    total: int


@dataclass(frozen=True)
class FailureRow:
    """Failed payment plus its recovery case status when one exists."""

    payment: Payment
    recovery_status: RecoveryStatus | None


@dataclass(frozen=True)
class FailurePageResult:
    """One page of failed payments and the unfiltered total."""

    items: list[FailureRow]
    total: int


def _count(db: Session, model: type[Any], *clauses: Any) -> int:
    """Return ``COUNT(*)`` for ``model`` filtered by ``clauses``."""
    stmt = select(func.count()).select_from(model)
    if clauses:
        stmt = stmt.where(*clauses)
    return int(db.scalar(stmt) or 0)


def require_merchant(db: Session, merchant_id: UUID) -> Merchant:
    """Load a merchant or raise ``MerchantNotFoundError``.

    Args:
        db: Request-scoped SQLAlchemy session.
        merchant_id: Primary key to look up.

    Returns:
        The matching ``Merchant`` row.

    Raises:
        MerchantNotFoundError: When no row exists for ``merchant_id``.
    """
    merchant = db.get(Merchant, merchant_id)
    if merchant is None:
        logger.info("merchant.not_found", extra={"merchant_id": str(merchant_id)})
        raise MerchantNotFoundError(merchant_id)
    return merchant


def get_metrics(db: Session, merchant_id: UUID) -> MerchantMetric | None:
    """Return the precomputed metrics snapshot, or ``None`` if none exists.

    Args:
        db: Request-scoped SQLAlchemy session.
        merchant_id: Merchant whose snapshot is requested.

    Returns:
        The ``merchant_metrics`` row, or ``None``.

    Raises:
        MerchantNotFoundError: When the merchant does not exist.
    """
    require_merchant(db, merchant_id)
    logger.info("merchant.metrics", extra={"merchant_id": str(merchant_id)})
    return db.scalar(
        select(MerchantMetric).where(MerchantMetric.merchant_id == merchant_id)
    )


def get_summary(db: Session, merchant_id: UUID) -> MerchantSummaryResult:
    """Load profile, ledger counts, and metrics for the dashboard header.

    Args:
        db: Request-scoped SQLAlchemy session.
        merchant_id: Merchant whose summary is requested.

    Returns:
        Counts are live ``COUNT(*)`` queries, not cached metrics.

    Raises:
        MerchantNotFoundError: When the merchant does not exist.
    """
    merchant = require_merchant(db, merchant_id)
    failed_clause = (
        Payment.merchant_id == merchant_id,
        Payment.payment_status == PaymentStatus.FAILED,
    )
    result = MerchantSummaryResult(
        merchant=merchant,
        customers=_count(db, Customer, Customer.merchant_id == merchant_id),
        subscriptions=_count(db, Subscription, Subscription.merchant_id == merchant_id),
        payments=_count(db, Payment, Payment.merchant_id == merchant_id),
        failed_payments=_count(db, Payment, *failed_clause),
        recovery_cases=_count(db, RecoveryCase, RecoveryCase.merchant_id == merchant_id),
        metrics=db.scalar(
            select(MerchantMetric).where(MerchantMetric.merchant_id == merchant_id)
        ),
    )
    logger.info(
        "merchant.summary",
        extra={
            "merchant_id": str(merchant_id),
            "customers": result.customers,
            "payments": result.payments,
            "failed_payments": result.failed_payments,
        },
    )
    return result


def list_payments(
    db: Session,
    merchant_id: UUID,
    *,
    offset: int,
    limit: int,
) -> PaymentPageResult:
    """Return one page of payments newest-first.

    Args:
        db: Request-scoped SQLAlchemy session.
        merchant_id: Merchant whose ledger is listed.
        offset: SQL offset (already normalized).
        limit: Page length (already clamped).

    Returns:
        Page rows plus the total matching count.

    Raises:
        MerchantNotFoundError: When the merchant does not exist.
    """
    require_merchant(db, merchant_id)
    total = _count(db, Payment, Payment.merchant_id == merchant_id)
    items = list(
        db.scalars(
            select(Payment)
            .where(Payment.merchant_id == merchant_id)
            .order_by(Payment.created_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()
    )
    logger.info(
        "merchant.payments",
        extra={
            "merchant_id": str(merchant_id),
            "offset": offset,
            "limit": limit,
            "total": total,
        },
    )
    return PaymentPageResult(items=items, total=total)


def list_failures(
    db: Session,
    merchant_id: UUID,
    *,
    offset: int,
    limit: int,
) -> FailurePageResult:
    """Return one page of failed payments newest-first.

    Joins ``recovery_cases`` so the dashboard can show journey status.
    ``payment_id`` is unique on recovery cases, so the join is at most 1:1.

    Args:
        db: Request-scoped SQLAlchemy session.
        merchant_id: Merchant whose failure queue is listed.
        offset: SQL offset (already normalized).
        limit: Page length (already clamped).

    Returns:
        Failed payment rows plus the total matching count.

    Raises:
        MerchantNotFoundError: When the merchant does not exist.
    """
    require_merchant(db, merchant_id)
    failed = (
        Payment.merchant_id == merchant_id,
        Payment.payment_status == PaymentStatus.FAILED,
    )
    total = _count(db, Payment, *failed)
    rows = db.execute(
        select(Payment, RecoveryCase.recovery_status)
        .outerjoin(RecoveryCase, RecoveryCase.payment_id == Payment.id)
        .where(*failed)
        .order_by(Payment.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    items = [
        FailureRow(payment=payment, recovery_status=status) for payment, status in rows
    ]
    logger.info(
        "merchant.failures",
        extra={
            "merchant_id": str(merchant_id),
            "offset": offset,
            "limit": limit,
            "total": total,
        },
    )
    return FailurePageResult(items=items, total=total)
