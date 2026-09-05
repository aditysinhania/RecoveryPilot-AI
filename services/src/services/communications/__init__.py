"""Sandbox communication adapters (SMS, WhatsApp, Email). Swappable providers."""

from services.communications.models import DeliveryResult, OutboundMessage
from services.communications.mock_providers import (
    MockEmailProvider,
    MockSmsProvider,
    MockWhatsAppProvider,
    default_providers,
)
from services.communications.rate_limit import RateLimiter
from services.communications.router import CommunicationRouter

__all__ = [
    "CommunicationRouter",
    "DeliveryResult",
    "MockEmailProvider",
    "MockSmsProvider",
    "MockWhatsAppProvider",
    "OutboundMessage",
    "RateLimiter",
    "default_providers",
]
