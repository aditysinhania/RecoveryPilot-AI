"""Orchestrate generation, write CSV/JSON artefacts, and validate referential quality."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

from simulator.config import GeneratorConfig
from simulator.distributions import SeededRNG
from simulator.event_generator import build_ecosystem
from simulator.webhook_generator import generate_webhooks

logger = logging.getLogger(__name__)

CSV_TABLES: tuple[str, ...] = (
    "customers",
    "subscriptions",
    "payments",
    "recovery_cases",
    "recovery_actions",
    "promises_to_pay",
    "audit_logs",
    "merchant_metrics",
    "webhook_events",
)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    frame = pd.DataFrame(rows)
    frame.to_csv(path, index=False)
    logger.info("dataset.csv", extra={"path": str(path), "rows": len(rows)})


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    logger.info("dataset.json", extra={"path": str(path)})


def validate_dataset(cfg: GeneratorConfig, data: dict[str, Any]) -> dict[str, Any]:
    """Check FK integrity, coverage, date window, and plan amounts."""
    from datetime import datetime

    customers = {row["id"] for row in data["customers"]}
    subscriptions = {row["id"]: row for row in data["subscriptions"]}
    payments = {row["id"]: row for row in data["payments"]}
    cases = {row["id"]: row for row in data["recovery_cases"]}
    original_failed = {row["id"] for row in data["failed_payments"]}
    case_payments = {row["payment_id"] for row in data["recovery_cases"]}
    errors: list[str] = []

    for sub in data["subscriptions"]:
        if sub["customer_id"] not in customers:
            errors.append(f"orphan subscription customer {sub['id']}")
        plan = sub.get("plan_name")
        if plan and int(sub["billing_amount"]) != cfg.plan_paise[plan]:
            errors.append(f"plan amount mismatch {sub['id']}")

    for pay in data["payments"]:
        if pay["customer_id"] not in customers:
            errors.append(f"orphan payment customer {pay['id']}")
        if pay.get("subscription_id") and pay["subscription_id"] not in subscriptions:
            errors.append(f"orphan payment subscription {pay['id']}")
        created = datetime.fromisoformat(str(pay["created_at"]))
        if created < cfg.window_start or created > cfg.as_of:
            errors.append(f"payment outside window {pay['id']}")

    missing_cases = original_failed - case_payments
    if missing_cases:
        errors.append(f"failed payments without cases: {len(missing_cases)}")
    for action in data["recovery_actions"]:
        if action["recovery_case_id"] not in cases:
            errors.append(f"orphan action {action['id']}")
    for promise in data["promises_to_pay"]:
        if promise["recovery_case_id"] not in cases:
            errors.append(f"orphan promise {promise['id']}")
    for audit in data["audit_logs"]:
        if audit["recovery_case_id"] not in cases:
            errors.append(f"orphan audit {audit['id']}")

    webhook_missing = sum(
        1
        for hook in data["webhook_events"]
        if hook.get("payment_id") and hook["payment_id"] not in payments
    )
    if webhook_missing:
        errors.append(f"webhooks referencing missing payments: {webhook_missing}")

    report = {
        "ok": not errors,
        "error_count": len(errors),
        "errors": errors[:50],
        "counts": {name: len(data.get(name, [])) for name in CSV_TABLES},
        "failed_payments": len(original_failed),
        "recovery_cases": len(cases),
        "duplicate_webhook_event_ids": len(data["webhook_events"])
        - len({row["razorpay_event_id"] for row in data["webhook_events"]}),
    }
    logger.info("dataset.validation", extra={"ok": report["ok"], "errors": report["error_count"]})
    return report


def generate_and_write(cfg: GeneratorConfig | None = None) -> dict[str, Any]:
    """Build the ecosystem, persist artefacts, and return the in-memory bundle."""
    cfg = cfg or GeneratorConfig()
    logger.info("dataset.start", extra={"seed": cfg.seed, "output_dir": str(cfg.output_dir)})
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    data = build_ecosystem(cfg)
    rng = SeededRNG(cfg.seed + 7)
    data["webhook_events"] = generate_webhooks(cfg, rng, data["payments"], data["subscriptions"])

    for name in CSV_TABLES:
        _write_csv(cfg.output_dir / f"{name}.csv", data[name])

    outage_payload = [
        {
            "outage_id": o.outage_id,
            "institution": o.institution,
            "rail": o.rail,
            "failure_reason": o.failure_reason,
            "started_at": o.started_at.isoformat(),
            "ended_at": o.ended_at.isoformat(),
            "summary": o.summary,
        }
        for o in data["outages"]
    ]
    _write_json(cfg.output_dir / "outage_events.json", outage_payload)

    metrics = data["merchant_metrics"][0]
    baseline = data["baseline"]
    summary = {
        "seed": cfg.seed,
        "merchant": cfg.merchant_name,
        "as_of": cfg.as_of.isoformat(),
        "lookback_days": cfg.lookback_days,
        "counts": {name: len(data[name]) for name in CSV_TABLES},
        "failed_payments": len(data["failed_payments"]),
    }
    merchant_summary = {
        "merchant": data["merchant"],
        "plans": cfg.plan_paise,
        "metrics": metrics,
        "city": cfg.city,
        "timezone": cfg.timezone,
    }
    simulation_summary = {
        "ai": {
            "recovered_revenue": metrics["recovered_revenue"],
            "revenue_at_risk": metrics["revenue_at_risk"],
            "recovery_rate": metrics["recovery_rate"],
            "suppressed_revenue": metrics["suppressed_revenue"],
            "escalation_count": metrics["escalation_count"],
            "policy_stop_count": metrics["policy_stop_count"],
            "average_recovery_hours": metrics["average_recovery_hours"],
        },
        "baseline": baseline,
        "lift_recovered_revenue": metrics["recovered_revenue"] - baseline["recovered_revenue"],
        "harmful_retries_avoided": baseline["harmful_retries"],
    }
    _write_json(cfg.output_dir / "dataset_summary.json", summary)
    _write_json(cfg.output_dir / "merchant_summary.json", merchant_summary)
    _write_json(cfg.output_dir / "simulation_summary.json", simulation_summary)
    _write_json(cfg.output_dir / "communication_costs.json", data["communication_costs"])
    _write_json(cfg.output_dir / "customer_behaviour.json", data["customer_behaviour"])
    _write_json(cfg.output_dir / "festival_calendar.json", data["festival_calendar"])

    report = validate_dataset(cfg, data)
    _write_json(cfg.output_dir / "validation_report.json", report)
    return data


def main() -> None:
    """CLI entry: write the seed=42 FitLife dataset under simulator/output/."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    generate_and_write(GeneratorConfig())


if __name__ == "__main__":
    main()
