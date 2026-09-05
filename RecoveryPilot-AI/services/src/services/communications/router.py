"""Channel router: policy allow-list, consent, and rate limits before mock send."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from services.communications.constants import SUPPORTED_CHANNELS
from services.communications.mock_providers import default_providers
from services.communications.models import DeliveryResult, OutboundMessage
from services.communications.ports import CommunicationProvider
from services.communications.rate_limit import RateLimiter

logger = logging.getLogger(__name__)


class CommunicationRouter:
    """Pick an allowed channel and send through a swappable sandbox provider."""

    def __init__(
        self,
        providers: dict[str, CommunicationProvider] | None = None,
        limiter: RateLimiter | None = None,
    ) -> None:
        self._providers = providers or default_providers()
        self._limiter = limiter or RateLimiter()

    def deliver(
        self,
        *,
        recovery_case_id: UUID,
        merchant_id: UUID | None,
        recommended: list[str],
        allowed: list[str],
        blocked: list[str],
        silent: bool,
        consent_granted: bool,
        contact_by_channel: dict[str, str],
        template: str,
        body: str,
        idempotency_key: str,
        request_id: str,
        correlation_id: str,
    ) -> list[DeliveryResult]:
        """Send at most one message on the first eligible channel.

        Args:
            recovery_case_id: Case being recovered.
            merchant_id: Tenant used for rate-limit buckets.
            recommended: Planner channel ranking.
            allowed: Policy allow-list.
            blocked: Policy block-list (always skipped).
            silent: When True, skip all customer notify (RETRY_SILENTLY).
            consent_granted: Umbrella consent gate.
            contact_by_channel: Masked destination per channel.
            template: Template id for the audit payload.
            body: Message body. Must not contain PAN/VPA.
            idempotency_key: Shared with the Razorpay action.
            request_id: HTTP request id.
            correlation_id: Workflow correlation id.

        Returns:
            Zero or one delivery result. Skips are recorded as skipped results.
        """
        if silent:
            logger.info(
                "comms.skip.silent",
                extra={"recovery_case_id": str(recovery_case_id)},
            )
            return [
                DeliveryResult(
                    channel="NONE",
                    status="SKIPPED",
                    provider="sandbox_mock",
                    skipped_reason="RETRY_SILENTLY",
                )
            ]
        if not consent_granted:
            logger.info(
                "comms.skip.consent",
                extra={"recovery_case_id": str(recovery_case_id)},
            )
            return [
                DeliveryResult(
                    channel="NONE",
                    status="SKIPPED",
                    provider="sandbox_mock",
                    skipped_reason="CONSENT_WITHDRAWN",
                )
            ]
        blocked_set = {item.lower() for item in blocked}
        allowed_set = {item.lower() for item in allowed} if allowed else {c.lower() for c in SUPPORTED_CHANNELS}
        ranked = recommended or list(SUPPORTED_CHANNELS)
        for channel in ranked:
            if channel.lower() in blocked_set:
                continue
            if channel.lower() not in allowed_set:
                continue
            provider = self._providers.get(channel)
            if provider is None:
                continue
            merchant_key = str(merchant_id) if merchant_id else "global"
            if not self._limiter.allow(merchant_key=merchant_key, channel=channel):
                return [
                    DeliveryResult(
                        channel=channel,
                        status="FAILED",
                        provider=provider.provider_name,
                        rate_limited=True,
                        skipped_reason="RATE_LIMITED",
                    )
                ]
            destination = contact_by_channel.get(channel) or contact_by_channel.get(channel.lower()) or "sandbox"
            message = OutboundMessage(
                channel=channel,
                recovery_case_id=recovery_case_id,
                merchant_id=merchant_id,
                to=destination,
                template=template,
                body=body,
                idempotency_key=f"{idempotency_key}:{channel}",
                request_id=request_id,
                correlation_id=correlation_id,
            )
            result = provider.send(message)
            logger.info(
                "comms.sent",
                extra={
                    "recovery_case_id": str(recovery_case_id),
                    "channel": channel,
                    "status": result.status,
                },
            )
            return [result]
        logger.info(
            "comms.skip.no_channel",
            extra={"recovery_case_id": str(recovery_case_id)},
        )
        return [
            DeliveryResult(
                channel="NONE",
                status="SKIPPED",
                provider="sandbox_mock",
                skipped_reason="NO_ALLOWED_CHANNEL",
                sent_at=datetime.now(UTC),
            )
        ]
