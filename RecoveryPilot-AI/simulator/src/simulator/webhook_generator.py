"""Razorpay webhook inbox: real event types, duplicates, signature flags."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any

from simulator.config import GeneratorConfig, deterministic_uuid
from simulator.distributions import SeededRNG, razorpay_id

logger = logging.getLogger(__name__)

STATUS_TO_EVENT: dict[str, str] = {
    "FAILED": "payment.failed",
    "CAPTURED": "payment.captured",
    "RECOVERED": "payment.captured",
    "AUTHORIZED": "payment.authorized",
}


def generate_webhooks(
    cfg: GeneratorConfig,
    rng: SeededRNG,
    payments: list[dict[str, Any]],
    _subscriptions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build ~n_webhook_events rows, including intentional duplicate deliveries."""
    rows: list[dict[str, Any]] = []
    unique_target = int(cfg.n_webhook_events * (1.0 - cfg.webhook_duplicate_rate))
    pool = list(payments)
    rng.random.shuffle(pool)
    selected = pool[: min(len(pool), unique_target)]

    for index, payment in enumerate(selected):
        created = datetime.fromisoformat(str(payment["created_at"]))
        event_type = STATUS_TO_EVENT.get(str(payment["payment_status"]), "payment.authorized")
        if str(payment["payment_status"]) == "CAPTURED" and rng.chance(0.08):
            event_type = "payment_link.paid"
        if str(payment.get("subscription_id")) and rng.chance(0.12):
            event_type = (
                "subscription.cancelled"
                if payment["payment_status"] == "FAILED"
                else "subscription.charged"
            )
        event_id = razorpay_id(cfg.seed, "evt", f"{index}:{payment['id']}")
        payload = {
            "event": event_type,
            "payload": {
                "payment": {
                    "entity": {
                        "id": payment["razorpay_payment_id"],
                        "order_id": payment["razorpay_order_id"],
                        "amount": payment["amount"],
                        "currency": "INR",
                        "status": str(payment["payment_status"]).lower(),
                        "method": str(payment["payment_method"]).lower(),
                    }
                }
            },
            "created_at": int(created.timestamp()),
        }
        processed = created + timedelta(seconds=rng.randint(8, 180))
        rows.append(
            {
                "id": str(deterministic_uuid(cfg.seed, "webhook", str(index))),
                "razorpay_event_id": event_id,
                "event_type": event_type,
                "payload": json.dumps(payload, sort_keys=True),
                "signature_verified": rng.chance(0.97),
                "processed_at": processed.isoformat(),
                "created_at": created.isoformat(),
                "payment_id": payment["id"],
            }
        )

    duplicates_needed = cfg.n_webhook_events - len(rows)
    for dup_i in range(max(0, duplicates_needed)):
        source = rows[dup_i % max(1, len(rows))]
        created = datetime.fromisoformat(str(source["created_at"])) + timedelta(seconds=30 + dup_i)
        rows.append(
            {
                "id": str(deterministic_uuid(cfg.seed, "webhook_dup", str(dup_i))),
                "razorpay_event_id": source["razorpay_event_id"],
                "event_type": source["event_type"],
                "payload": source["payload"],
                "signature_verified": source["signature_verified"],
                "processed_at": created.isoformat(),
                "created_at": created.isoformat(),
                "payment_id": source["payment_id"],
            }
        )

    logger.info("generator.webhooks", extra={"count": len(rows)})
    return rows[: cfg.n_webhook_events]
