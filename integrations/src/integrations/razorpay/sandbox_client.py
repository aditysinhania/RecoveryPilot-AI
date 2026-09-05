"""Razorpay Sandbox REST client. Never uses live keys or production charges.

When credentials are placeholders, responses are deterministic mock Sandbox
payloads so local/CI can run without a real Razorpay account.
"""

from __future__ import annotations

import hashlib
import logging
import os
from typing import Any
from uuid import UUID, uuid5

from integrations.razorpay.constants import (
    IDEMPOTENCY_HEADER,
    PAYMENT_LINK_EXPIRE_SECONDS,
    PLACEHOLDER_KEY_IDS,
    PLACEHOLDER_SECRETS,
    REQUEST_TIMEOUT_SECONDS,
    SANDBOX_BASE_URL,
    TRANSIENT_STATUS_CODES,
)
from integrations.razorpay.errors import (
    RazorpayError,
    RazorpayLiveKeyError,
    RazorpayPermanentError,
    RazorpayTransientError,
)
from integrations.razorpay.models import RazorpayResource

logger = logging.getLogger(__name__)

MOCK_NAMESPACE = UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")


def _short_token(kind: str, seed: str) -> str:
    """Stable Razorpay-like public id fragment."""
    return uuid5(MOCK_NAMESPACE, f"{kind}:{seed}").hex[:14]


class RazorpaySandboxClient:
    """Thin Sandbox wrapper. Does not choose recovery strategies."""

    def __init__(
        self,
        *,
        key_id: str,
        key_secret: str,
        base_url: str = SANDBOX_BASE_URL,
        transport: Any | None = None,
    ) -> None:
        self._key_id = (key_id or "").strip()
        self._key_secret = (key_secret or "").strip()
        self._base_url = base_url.rstrip("/")
        self._transport = transport
        self._mock_cache: dict[str, dict[str, Any]] = {}
        if self._key_id.startswith("rzp_live_"):
            raise RazorpayLiveKeyError("Razorpay live keys are not allowed")

    @classmethod
    def from_settings(cls) -> RazorpaySandboxClient:
        """Load test keys from Settings, else process environment."""
        key_id = os.environ.get("RAZORPAY_KEY_ID", "rzp_test_placeholder")
        key_secret = os.environ.get("RAZORPAY_KEY_SECRET", "placeholder_secret")
        try:
            from app.config.settings import Settings

            loaded = Settings()
            key_id = loaded.razorpay_key_id
            key_secret = loaded.razorpay_key_secret
        except Exception:  # noqa: BLE001 — integrations must run without FastAPI
            logger.info("razorpay.settings.fallback_env")
        return cls(key_id=key_id, key_secret=key_secret)

    def is_live_sandbox(self) -> bool:
        """True when test keys look real enough to call api.razorpay.com."""
        if self._key_id.startswith("rzp_live_"):
            return False
        if not self._key_id.startswith("rzp_test_"):
            return False
        if self._key_id in PLACEHOLDER_KEY_IDS:
            return False
        if self._key_secret in PLACEHOLDER_SECRETS:
            return False
        if "placeholder" in self._key_secret.lower():
            return False
        return len(self._key_secret) >= 8

    def create_payment_link(
        self,
        payload: dict[str, Any],
        *,
        idempotency_key: str,
    ) -> RazorpayResource:
        """POST /payment_links. Mocked when Sandbox credentials are placeholders."""
        logger.info(
            "razorpay.payment_link.start",
            extra={"idempotency_key": idempotency_key, "amount": payload.get("amount")},
        )
        body = self._post("/payment_links", payload, idempotency_key)
        resource = self._resource("payment_link", body)
        logger.info(
            "razorpay.payment_link.ok",
            extra={"idempotency_key": idempotency_key, "resource_id": resource.resource_id},
        )
        return resource

    def create_order(
        self,
        payload: dict[str, Any],
        *,
        idempotency_key: str,
    ) -> RazorpayResource:
        """POST /orders used as the retry-payment request in Sandbox."""
        logger.info(
            "razorpay.order.start",
            extra={"idempotency_key": idempotency_key, "amount": payload.get("amount")},
        )
        body = self._post("/orders", payload, idempotency_key)
        resource = self._resource("order", body)
        logger.info(
            "razorpay.order.ok",
            extra={"idempotency_key": idempotency_key, "resource_id": resource.resource_id},
        )
        return resource

    def create_mandate_session(
        self,
        payload: dict[str, Any],
        *,
        idempotency_key: str,
    ) -> RazorpayResource:
        """Hosted card/mandate update session via Payment Links in Sandbox."""
        notes = dict(payload.get("notes") or {})
        notes["purpose"] = "mandate_update"
        payload = {**payload, "notes": notes}
        logger.info("razorpay.mandate_session.start", extra={"idempotency_key": idempotency_key})
        body = self._post("/payment_links", payload, f"{idempotency_key}:mandate")
        resource = self._resource("mandate_session", body)
        logger.info(
            "razorpay.mandate_session.ok",
            extra={"idempotency_key": idempotency_key, "resource_id": resource.resource_id},
        )
        return resource

    def _post(self, path: str, payload: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        """POST JSON to Sandbox, or return a cached mock body."""
        if not self.is_live_sandbox():
            return self._mock_body(path, payload, idempotency_key)
        try:
            import httpx
        except ImportError as exc:  # pragma: no cover — workspace always has httpx
            raise RazorpayError("httpx is required for live Sandbox calls") from exc
        url = f"{self._base_url}{path}"
        headers = {
            "Content-Type": "application/json",
            IDEMPOTENCY_HEADER: idempotency_key,
        }
        try:
            with httpx.Client(
                timeout=REQUEST_TIMEOUT_SECONDS,
                transport=self._transport,
                auth=(self._key_id, self._key_secret),
            ) as client:
                response = client.post(url, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            logger.info("razorpay.http.timeout", extra={"path": path})
            raise RazorpayTransientError("Razorpay Sandbox timed out", status_code=408) from exc
        except httpx.TransportError as exc:
            logger.info("razorpay.http.transport", extra={"error_type": type(exc).__name__})
            raise RazorpayTransientError("Razorpay Sandbox transport error") from exc
        if response.status_code in TRANSIENT_STATUS_CODES:
            raise RazorpayTransientError(
                f"Razorpay Sandbox transient HTTP {response.status_code}",
                status_code=response.status_code,
            )
        if response.status_code >= 400:
            raise RazorpayPermanentError(
                f"Razorpay Sandbox rejected the request ({response.status_code})",
                status_code=response.status_code,
            )
        body = response.json()
        if not isinstance(body, dict):
            raise RazorpayPermanentError("Razorpay Sandbox returned a non-object body")
        return body

    def _mock_body(self, path: str, payload: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        """Deterministic Sandbox-shaped JSON keyed by the idempotency token."""
        cached = self._mock_cache.get(idempotency_key)
        if cached is not None:
            logger.info("razorpay.mock.replay", extra={"idempotency_key": idempotency_key})
            return cached
        amount = int(payload.get("amount") or 0)
        currency = str(payload.get("currency") or "INR")
        digest = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()[:10]
        if path.endswith("/orders"):
            body = {
                "id": f"order_{_short_token('order', idempotency_key)}",
                "entity": "order",
                "amount": amount,
                "currency": currency,
                "status": "created",
                "receipt": payload.get("receipt"),
                "notes": payload.get("notes") or {},
                "mock": True,
                "fingerprint": digest,
            }
        else:
            link_id = f"plink_{_short_token('plink', idempotency_key)}"
            purpose = (payload.get("notes") or {}).get("purpose")
            entity = "mandate_session" if purpose == "mandate_update" else "payment_link"
            body = {
                "id": link_id if entity == "payment_link" else f"cs_{_short_token('card', idempotency_key)}",
                "entity": entity,
                "amount": amount,
                "currency": currency,
                "status": "created",
                "short_url": f"https://rzp.io/i/{digest}",
                "expire_by": PAYMENT_LINK_EXPIRE_SECONDS,
                "notes": payload.get("notes") or {},
                "mock": True,
                "fingerprint": digest,
            }
        self._mock_cache[idempotency_key] = body
        return body

    def _resource(self, resource_type: str, body: dict[str, Any]) -> RazorpayResource:
        """Normalize a Razorpay JSON body into a resource DTO."""
        return RazorpayResource(
            resource_type=resource_type,
            resource_id=str(body.get("id") or ""),
            status=str(body.get("status") or "created"),
            short_url=body.get("short_url"),
            amount=int(body["amount"]) if body.get("amount") is not None else None,
            currency=str(body.get("currency") or "INR"),
            mock=bool(body.get("mock", not self.is_live_sandbox())),
            raw=body,
        )
