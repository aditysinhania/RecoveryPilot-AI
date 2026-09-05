"""FastAPI adapter over the domain merchant service.

Maps ORM results onto dashboard Pydantic models and domain misses onto
HTTP exceptions. SQL stays in ``services.merchant_service``.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import MerchantNotFoundError
from app.schemas.merchant_dashboard import (
    FailureListItem,
    MerchantMetricsPayload,
    MerchantSummary,
    PaymentListItem,
)
from database.models import MerchantMetric
from services.merchant_service import FailurePageResult
from services.merchant_service import MerchantNotFoundError as DomainMerchantNotFound
from services.merchant_service import PaymentPageResult
from services.merchant_service import get_metrics as load_metrics
from services.merchant_service import get_summary as load_summary
from services.merchant_service import list_failures as load_failures
from services.merchant_service import list_payments as load_payments
from shared.schemas.merchant import MerchantRead


def _map_not_found(exc: DomainMerchantNotFound) -> MerchantNotFoundError:
    """Convert a domain miss into the HTTP 404 exception."""
    return MerchantNotFoundError(f"Merchant not found: {exc.merchant_id}")


def _metrics_payload(merchant_id: UUID, row: MerchantMetric | None) -> MerchantMetricsPayload:
    """Build a metrics DTO, using zeros when no snapshot row exists."""
    if row is None:
        return MerchantMetricsPayload(merchant_id=merchant_id)
    return MerchantMetricsPayload.model_validate(row)


def _payment_items(page: PaymentPageResult) -> list[PaymentListItem]:
    """Map payment ORM rows onto dashboard list items."""
    return [PaymentListItem.model_validate(row) for row in page.items]


def _failure_items(page: FailurePageResult) -> list[FailureListItem]:
    """Map failed payments onto dashboard list items including recovery status."""
    items: list[FailureListItem] = []
    for row in page.items:
        item = FailureListItem.model_validate(row.payment)
        items.append(item.model_copy(update={"recovery_status": row.recovery_status}))
    return items


def get_summary(db: Session, merchant_id: UUID) -> MerchantSummary:
    """Return the dashboard header payload for ``merchant_id``.

    Args:
        db: Request-scoped SQLAlchemy session.
        merchant_id: Merchant to load.

    Returns:
        Profile, live counts, and metrics (zeros if none).

    Raises:
        MerchantNotFoundError: When the merchant does not exist.
    """
    try:
        result = load_summary(db, merchant_id)
    except DomainMerchantNotFound as exc:
        raise _map_not_found(exc) from exc
    return MerchantSummary(
        merchant=MerchantRead.model_validate(result.merchant),
        customers=result.customers,
        subscriptions=result.subscriptions,
        payments=result.payments,
        failed_payments=result.failed_payments,
        recovery_cases=result.recovery_cases,
        metrics=_metrics_payload(merchant_id, result.metrics),
    )


def get_metrics(db: Session, merchant_id: UUID) -> MerchantMetricsPayload:
    """Return the metrics snapshot for ``merchant_id``.

    Args:
        db: Request-scoped SQLAlchemy session.
        merchant_id: Merchant to load.

    Returns:
        Snapshot fields, or zeros when no ``merchant_metrics`` row exists.

    Raises:
        MerchantNotFoundError: When the merchant does not exist.
    """
    try:
        row = load_metrics(db, merchant_id)
    except DomainMerchantNotFound as exc:
        raise _map_not_found(exc) from exc
    return _metrics_payload(merchant_id, row)


def list_payments(
    db: Session,
    merchant_id: UUID,
    *,
    offset: int,
    limit: int,
) -> tuple[list[PaymentListItem], int]:
    """Return one page of payments and the matching total.

    Args:
        db: Request-scoped SQLAlchemy session.
        merchant_id: Merchant whose ledger is listed.
        offset: SQL offset.
        limit: Page length.

    Returns:
        ``(items, total)`` ready for ``PaginatedResponse``.

    Raises:
        MerchantNotFoundError: When the merchant does not exist.
    """
    try:
        page = load_payments(db, merchant_id, offset=offset, limit=limit)
    except DomainMerchantNotFound as exc:
        raise _map_not_found(exc) from exc
    return _payment_items(page), page.total


def list_failures(
    db: Session,
    merchant_id: UUID,
    *,
    offset: int,
    limit: int,
) -> tuple[list[FailureListItem], int]:
    """Return one page of failed payments and the matching total.

    Args:
        db: Request-scoped SQLAlchemy session.
        merchant_id: Merchant whose failure queue is listed.
        offset: SQL offset.
        limit: Page length.

    Returns:
        ``(items, total)`` ready for ``PaginatedResponse``.

    Raises:
        MerchantNotFoundError: When the merchant does not exist.
    """
    try:
        page = load_failures(db, merchant_id, offset=offset, limit=limit)
    except DomainMerchantNotFound as exc:
        raise _map_not_found(exc) from exc
    return _failure_items(page), page.total
