"""Consent and channel allow-lists. Pure functions, no I/O."""

from __future__ import annotations

from services.policy.constants import CHANNELS
from services.policy.models import CustomerPolicySnapshot
from shared.enums import ConsentStatus


def channel_granted(customer: CustomerPolicySnapshot) -> dict[str, bool]:
    """Map display channel names onto the customer's consent flags.

    Args:
        customer: Policy snapshot (per-channel flags may be inferred by the service).

    Returns:
        WhatsApp / SMS / Voice / Email granted map.
    """
    if customer.consent_status == ConsentStatus.WITHDRAWN:
        return {name: False for name in CHANNELS}
    if customer.consent_status == ConsentStatus.PENDING:
        return {name: False for name in CHANNELS}
    return {
        "WhatsApp": customer.consent_whatsapp,
        "SMS": customer.consent_sms,
        "Voice": customer.consent_voice,
        "Email": customer.consent_email,
    }


def split_channels(customer: CustomerPolicySnapshot) -> tuple[list[str], list[str]]:
    """Return ``(allowed, blocked)`` channel lists from consent alone.

    Args:
        customer: Policy snapshot.

    Returns:
        Allowed channels then blocked channels, both in registry order.
    """
    granted = channel_granted(customer)
    allowed = [name for name in CHANNELS if granted.get(name)]
    blocked = [name for name in CHANNELS if not granted.get(name)]
    return allowed, blocked


def consent_revoked(customer: CustomerPolicySnapshot) -> bool:
    """True when the customer withdrew all recovery communication."""
    return customer.consent_status == ConsentStatus.WITHDRAWN


def consent_pending(customer: CustomerPolicySnapshot) -> bool:
    """True when outreach is not yet permitted."""
    return customer.consent_status == ConsentStatus.PENDING
