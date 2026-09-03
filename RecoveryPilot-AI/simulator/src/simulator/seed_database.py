"""Hydrate Postgres from generated CSV/JSON. No ORM insertion — pandas read_sql for speed."""

from __future__ import annotations

import json
import logging

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from simulator.config import GeneratorConfig

logger = logging.getLogger(__name__)

TABLE_ORDER: tuple[str, ...] = (
    "merchants",
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

CSV_TO_TABLE: dict[str, str] = {
    "customers": "customers",
    "subscriptions": "subscriptions",
    "payments": "payments",
    "recovery_cases": "recovery_cases",
    "recovery_actions": "recovery_actions",
    "promises_to_pay": "promises_to_pay",
    "audit_logs": "audit_logs",
    "merchant_metrics": "merchant_metrics",
    "webhook_events": "webhook_events",
}

DROP_BY_TABLE: dict[str, set[str]] = {
    "customers": {"consent_whatsapp", "consent_sms", "consent_voice", "salary_dependent"},
    "subscriptions": {"plan_name", "billing_day", "started_at", "renewal_count"},
    "payments": {"plan_name", "salary_dependent", "segment", "is_original_failure", "payment_time"},
    "recovery_cases": {"journey", "ai_recovered", "ai_suppressed", "ai_escalated", "amount"},
    "promises_to_pay": {"paid_amount"},
    "merchant_metrics": {"average_recovery_hours"},
    "webhook_events": {"payment_id"},
}

JSON_COLUMNS: dict[str, tuple[str, ...]] = {
    "recovery_actions": ("metadata",),
    "audit_logs": ("structured_payload",),
    "webhook_events": ("payload",),
}


def seed_database(db: Session, cfg: GeneratorConfig | None = None) -> dict[str, int]:
    """Truncate domain tables and bulk-insert from the output directory.

    Args:
        db: Active SQLAlchemy session (engine with ``INSERT`` permission).
        cfg: Generator config; uses ``cfg.output_dir`` to locate CSVs.

    Returns:
        Row counts by table name.
    """
    cfg = cfg or GeneratorConfig()
    out = cfg.output_dir
    counts: dict[str, int] = {}

    for table in reversed(TABLE_ORDER):
        db.execute(text(f'TRUNCATE TABLE "{table}" CASCADE'))
    db.commit()
    logger.info("seed.truncated")

    merchant_json = out / "merchant_summary.json"
    if merchant_json.exists():
        merchant_data = json.loads(merchant_json.read_text(encoding="utf-8"))["merchant"]
        cols = [
            "id", "merchant_name", "business_category", "email",
            "phone", "razorpay_account_id", "timezone", "created_at", "updated_at",
        ]
        row_data = {col: merchant_data[col] for col in cols}
        frame = pd.DataFrame([row_data])
        frame.to_sql("merchants", db.get_bind(), if_exists="append", index=False)
        counts["merchants"] = 1

    for csv_name, table_name in CSV_TO_TABLE.items():
        csv_path = out / f"{csv_name}.csv"
        if not csv_path.exists():
            logger.warning("seed.missing_csv", extra={"path": str(csv_path)})
            continue
        frame = pd.read_csv(csv_path)
        if table_name == "recovery_actions" and "action_metadata" in frame.columns:
            frame = frame.rename(columns={"action_metadata": "metadata"})
        drop_cols = [col for col in DROP_BY_TABLE.get(table_name, set()) if col in frame.columns]
        if drop_cols:
            frame = frame.drop(columns=drop_cols)
        for col in JSON_COLUMNS.get(table_name, ()):
            if col in frame.columns:
                frame[col] = frame[col].fillna("{}").map(
                    lambda value: json.loads(value) if isinstance(value, str) else value
                )
        if table_name == "webhook_events" and "razorpay_event_id" in frame.columns:
            frame = frame.drop_duplicates(subset=["razorpay_event_id"], keep="first")
        frame.to_sql(table_name, db.get_bind(), if_exists="append", index=False)
        counts[table_name] = len(frame)
        logger.info("seed.loaded", extra={"table": table_name, "rows": len(frame)})

    db.commit()
    logger.info("seed.done", extra={"counts": counts})
    return counts
