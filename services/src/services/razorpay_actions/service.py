"""Map planner strategies onto Razorpay Sandbox calls. No planner logic changes."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from services.planner.models import PlannerStrategy
from services.razorpay_actions.constants import (
    MANDATE_SESSION_TTL,
    PAYMENT_LINK_TTL,
    RAZORPAY_STRATEGIES,
)
from services.razorpay_actions.errors import (
    RazorpayActionPermanentError,
    RazorpayActionTransientError,
)
from services.razorpay_actions.models import RazorpayActionRequest, RazorpayActionResult
from services.razorpay_actions.ports import RazorpayHttpPort

logger = logging.getLogger(__name__)


def _customer_block(request: RazorpayActionRequest) -> dict[str, str]:
    """Razorpay customer object. Phone/email are required by Payment Links."""
    return {
        "name": request.customer_name,
        "email": request.customer_email,
        "contact": request.customer_phone,
    }


def _notes(request: RazorpayActionRequest) -> dict[str, str]:
    """Attach case + idempotency without secrets."""
    notes = {
        "recovery_case_id": str(request.recovery_case_id),
        "idempotency_key": request.idempotency_key,
    }
    notes.update(request.notes)
    return notes


def _call(client_method: object, *args: object, **kwargs: object) -> object:
    """Invoke the HTTP port and map adapter errors onto domain errors."""
    try:
        return client_method(*args, **kwargs)  # type: ignore[operator]
    except RazorpayActionTransientError:
        raise
    except RazorpayActionPermanentError:
        raise
    except Exception as exc:
        name = type(exc).__name__
        if "Transient" in name or "Timeout" in name:
            raise RazorpayActionTransientError(str(exc)) from exc
        if "Permanent" in name or "LiveKey" in name:
            raise RazorpayActionPermanentError(str(exc)) from exc
        raise


def _from_resource(kind: str, resource: object) -> RazorpayActionResult:
    """Normalize a client resource (pydantic model or dict) into an action result."""
    if hasattr(resource, "model_dump"):
        data = resource.model_dump()  # type: ignore[no-untyped-call]
    elif isinstance(resource, dict):
        data = resource
    else:
        data = {
            "resource_id": getattr(resource, "resource_id", ""),
            "status": getattr(resource, "status", "created"),
            "short_url": getattr(resource, "short_url", None),
            "mock": getattr(resource, "mock", True),
            "raw": {},
        }
    return RazorpayActionResult(
        kind=kind,
        resource_id=str(data.get("resource_id") or data.get("id") or ""),
        status=str(data.get("status") or "created"),
        short_url=data.get("short_url"),
        mock=bool(data.get("mock", True)),
        payload=data.get("raw") if isinstance(data.get("raw"), dict) else data,
    )


class RazorpayActionService:
    """Strategy → Sandbox call. Does not plan, diagnose, or evaluate policy."""

    def __init__(self, client: RazorpayHttpPort) -> None:
        self._client = client

    def execute_strategy(
        self,
        strategy: PlannerStrategy,
        request: RazorpayActionRequest,
        *,
        as_of: datetime | None = None,
    ) -> RazorpayActionResult | None:
        """Run the Sandbox call for ``strategy``. Wait/stop/escalate return None.

        Args:
            strategy: Planner strategy. Not modified.
            request: Amount, customer, and idempotency.
            as_of: Clock for expiry timestamps.

        Returns:
            Sandbox result, or ``None`` when the strategy has no Razorpay call.
        """
        clock = as_of or datetime.now(UTC)
        if strategy not in RAZORPAY_STRATEGIES:
            logger.info(
                "razorpay_actions.skip",
                extra={"strategy": strategy.value, "recovery_case_id": str(request.recovery_case_id)},
            )
            return None
        if strategy in {PlannerStrategy.RETRY_PAYMENT, PlannerStrategy.RETRY_SILENTLY}:
            return self.retry_payment(request)
        if strategy == PlannerStrategy.REQUEST_NEW_MANDATE:
            return self.create_mandate_session(request, as_of=clock)
        return self.create_payment_link(request, as_of=clock, switch=strategy == PlannerStrategy.SWITCH_PAYMENT_METHOD)

    def create_payment_link(
        self,
        request: RazorpayActionRequest,
        *,
        as_of: datetime,
        switch: bool = False,
    ) -> RazorpayActionResult:
        """Create a Razorpay Payment Link (Sandbox)."""
        expire_by = int((as_of + PAYMENT_LINK_TTL).timestamp())
        notes = _notes(request)
        if switch:
            notes["purpose"] = "switch_payment_method"
        payload = {
            "amount": request.amount,
            "currency": request.currency,
            "accept_partial": False,
            "description": request.description,
            "customer": _customer_block(request),
            "notify": {"sms": False, "email": False},
            "reminder_enable": False,
            "notes": notes,
            "expire_by": expire_by,
        }
        logger.info(
            "razorpay_actions.payment_link",
            extra={"recovery_case_id": str(request.recovery_case_id), "amount": request.amount},
        )
        resource = _call(
            self._client.create_payment_link, payload, idempotency_key=request.idempotency_key
        )
        return _from_resource("payment_link", resource)

    def retry_payment(self, request: RazorpayActionRequest) -> RazorpayActionResult:
        """Submit a retry as a Sandbox order (idempotent)."""
        payload = {
            "amount": request.amount,
            "currency": request.currency,
            "receipt": f"rp-{request.recovery_case_id}",
            "notes": _notes(request),
        }
        logger.info(
            "razorpay_actions.retry",
            extra={"recovery_case_id": str(request.recovery_case_id), "amount": request.amount},
        )
        resource = _call(self._client.create_order, payload, idempotency_key=request.idempotency_key)
        return _from_resource("retry_order", resource)

    def create_mandate_session(
        self,
        request: RazorpayActionRequest,
        *,
        as_of: datetime,
    ) -> RazorpayActionResult:
        """Create a hosted card/mandate update session via Payment Links."""
        expire_by = int((as_of + MANDATE_SESSION_TTL).timestamp())
        payload = {
            "amount": request.amount,
            "currency": request.currency,
            "accept_partial": False,
            "description": request.description or "Update payment method",
            "customer": _customer_block(request),
            "notify": {"sms": False, "email": False},
            "reminder_enable": False,
            "notes": {**_notes(request), "purpose": "mandate_update"},
            "expire_by": expire_by,
        }
        logger.info(
            "razorpay_actions.mandate_session",
            extra={"recovery_case_id": str(request.recovery_case_id)},
        )
        resource = _call(
            self._client.create_mandate_session, payload, idempotency_key=request.idempotency_key
        )
        return _from_resource("mandate_session", resource)
