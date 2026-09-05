"""Swappable communication provider port. Implementations live beside this file."""

from __future__ import annotations

from typing import Protocol

from services.communications.models import DeliveryResult, OutboundMessage


class CommunicationProvider(Protocol):
    """Send one outbound message. Must not call a live SMS/WhatsApp/email API."""

    channel: str
    provider_name: str

    def send(self, message: OutboundMessage) -> DeliveryResult:
        """Deliver ``message`` or raise a transient/permanent adapter error."""
        ...
