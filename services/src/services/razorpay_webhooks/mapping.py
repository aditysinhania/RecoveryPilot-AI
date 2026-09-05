"""Pull payment / subscription identifiers and case notes from a Razorpay event body."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from services.razorpay_webhooks.constants import INGEST_KEY


def event_type_of(body: dict[str, Any]) -> str:
    """Return the Razorpay ``event`` string, or empty."""
    return str(body.get("event") or body.get("event_type") or "").strip()


def razorpay_event_id_of(body: dict[str, Any]) -> str:
    """Provider event id used for idempotency. Falls back to nested ``payload.id``."""
    token = body.get("id") or body.get("event_id") or body.get("razorpay_event_id")
    if token:
        return str(token).strip()[:128]
    payload = body.get("payload")
    if isinstance(payload, dict) and payload.get("id"):
        return str(payload["id"]).strip()[:128]
    return ""


def _entity(body: dict[str, Any], key: str) -> dict[str, Any]:
    """Return ``payload.<key>.entity`` or ``payload.<key>`` when present."""
    block = body.get("payload")
    if not isinstance(block, dict):
        block = body
    item = block.get(key)
    if not isinstance(item, dict):
        return {}
    entity = item.get("entity")
    if isinstance(entity, dict):
        return entity
    return item


def _notes(entity: dict[str, Any]) -> dict[str, Any]:
    """Razorpay notes object, or empty."""
    notes = entity.get("notes")
    return notes if isinstance(notes, dict) else {}


def case_id_from_notes(body: dict[str, Any]) -> UUID | None:
    """Parse ``notes.recovery_case_id`` from payment, link, or subscription entities."""
    for key in ("payment", "payment_link", "subscription", "order"):
        notes = _notes(_entity(body, key))
        raw = notes.get("recovery_case_id")
        if not raw:
            continue
        try:
            return UUID(str(raw))
        except ValueError:
            continue
    return None


def payment_provider_id(body: dict[str, Any]) -> str | None:
    """Razorpay payment id (``pay_``) when the payload includes a payment entity."""
    payment = _entity(body, "payment")
    token = payment.get("id")
    if token:
        return str(token)
    return None


def order_provider_id(body: dict[str, Any]) -> str | None:
    """Razorpay order id from payment or order entity."""
    payment = _entity(body, "payment")
    if payment.get("order_id"):
        return str(payment["order_id"])
    order = _entity(body, "order")
    if order.get("id"):
        return str(order["id"])
    return None


def payment_link_id(body: dict[str, Any]) -> str | None:
    """Payment link resource id when present."""
    link = _entity(body, "payment_link")
    if link.get("id"):
        return str(link["id"])
    return None


def subscription_provider_id(body: dict[str, Any]) -> str | None:
    """Razorpay subscription id when present."""
    sub = _entity(body, "subscription")
    if sub.get("id"):
        return str(sub["id"])
    payment = _entity(body, "payment")
    if payment.get("subscription_id"):
        return str(payment["subscription_id"])
    return None


def strip_ingest(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of the stored JSON without the local ingest envelope."""
    cloned = dict(payload)
    cloned.pop(INGEST_KEY, None)
    return cloned
