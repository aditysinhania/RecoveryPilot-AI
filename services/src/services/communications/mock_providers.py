"""Sandbox/mock SMS, WhatsApp, and Email providers. No carrier or SMTP calls."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import uuid5

from services.communications.constants import (
    CHANNEL_EMAIL,
    CHANNEL_SMS,
    CHANNEL_WHATSAPP,
    DEFAULT_PROVIDER,
)
from services.communications.models import DeliveryResult, OutboundMessage
from services.executor.constants import IDEMPOTENCY_NAMESPACE

logger = logging.getLogger(__name__)


def _message_id(channel: str, idempotency_key: str) -> str:
    """Stable mock provider id so webhook/idempotent replay stays deterministic."""
    return f"mock_{channel.lower()}_{uuid5(IDEMPOTENCY_NAMESPACE, idempotency_key).hex[:12]}"


class MockSmsProvider:
    """In-process SMS adapter. Never talks to a gateway."""

    channel: str = CHANNEL_SMS
    provider_name: str = DEFAULT_PROVIDER

    def send(self, message: OutboundMessage) -> DeliveryResult:
        """Record a mock SMS send and return a delivered result."""
        logger.info(
            "comms.sms.mock",
            extra={
                "recovery_case_id": str(message.recovery_case_id),
                "idempotency_key": message.idempotency_key,
            },
        )
        return DeliveryResult(
            channel=self.channel,
            status="DELIVERED",
            provider=self.provider_name,
            provider_message_id=_message_id("sms", message.idempotency_key),
            sent_at=datetime.now(UTC),
        )


class MockWhatsAppProvider:
    """In-process WhatsApp adapter. Never talks to Meta or Gupshup."""

    channel: str = CHANNEL_WHATSAPP
    provider_name: str = DEFAULT_PROVIDER

    def send(self, message: OutboundMessage) -> DeliveryResult:
        """Record a mock WhatsApp send and return a delivered result."""
        logger.info(
            "comms.whatsapp.mock",
            extra={
                "recovery_case_id": str(message.recovery_case_id),
                "idempotency_key": message.idempotency_key,
            },
        )
        return DeliveryResult(
            channel=self.channel,
            status="DELIVERED",
            provider=self.provider_name,
            provider_message_id=_message_id("wa", message.idempotency_key),
            sent_at=datetime.now(UTC),
        )


class MockEmailProvider:
    """In-process email adapter. Never opens SMTP."""

    channel: str = CHANNEL_EMAIL
    provider_name: str = DEFAULT_PROVIDER

    def send(self, message: OutboundMessage) -> DeliveryResult:
        """Record a mock email send and return a delivered result."""
        logger.info(
            "comms.email.mock",
            extra={
                "recovery_case_id": str(message.recovery_case_id),
                "idempotency_key": message.idempotency_key,
            },
        )
        return DeliveryResult(
            channel=self.channel,
            status="DELIVERED",
            provider=self.provider_name,
            provider_message_id=_message_id("em", message.idempotency_key),
            sent_at=datetime.now(UTC),
        )


def default_providers() -> dict[str, MockSmsProvider | MockWhatsAppProvider | MockEmailProvider]:
    """Return the sandbox provider map keyed by channel name."""
    sms = MockSmsProvider()
    whatsapp = MockWhatsAppProvider()
    email = MockEmailProvider()
    return {sms.channel: sms, whatsapp.channel: whatsapp, email.channel: email}
