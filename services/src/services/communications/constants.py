"""Sandbox communication adapter constants. No real carrier traffic."""

from __future__ import annotations

from datetime import timedelta

CHANNEL_SMS: str = "SMS"
CHANNEL_WHATSAPP: str = "WhatsApp"
CHANNEL_EMAIL: str = "Email"

SUPPORTED_CHANNELS: tuple[str, ...] = (CHANNEL_WHATSAPP, CHANNEL_SMS, CHANNEL_EMAIL)

# Token-bucket refill: tokens per minute per merchant+channel.
RATE_LIMITS: dict[str, int] = {
    CHANNEL_SMS: 10,
    CHANNEL_WHATSAPP: 20,
    CHANNEL_EMAIL: 30,
}

RATE_WINDOW: timedelta = timedelta(minutes=1)
DEFAULT_PROVIDER: str = "sandbox_mock"
