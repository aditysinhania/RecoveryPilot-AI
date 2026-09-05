"""Hydrate Postgres from generated CSV/JSON. No ORM insertion — pandas read_sql for speed."""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

# Allow `python simulator/src/simulator/seed_database.py` (script dir is not the package root).
_SRC_ROOT = Path(__file__).resolve().parents[1]
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

import pandas as pd  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

from simulator.config import GeneratorConfig  # noqa: E402

logger = logging.getLogger(__name__)

_DEFAULT_DATABASE_URL = (
    "postgresql+psycopg://recoverypilot:recoverypilot@127.0.0.1:5432/recoverypilot"
)

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

_INT_UDTS = frozenset({"int2", "int4", "int8"})
_INSERT_CHUNK = 500


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
    failures: list[str] = []

    for table in reversed(TABLE_ORDER):
        db.execute(text(f'TRUNCATE TABLE "{table}" CASCADE'))
    db.commit()
    logger.info("seed.truncated")

    try:
        merchant_json = out / "merchant_summary.json"
        if not merchant_json.exists():
            raise FileNotFoundError(merchant_json)
        merchant_data = json.loads(merchant_json.read_text(encoding="utf-8"))["merchant"]
        cols = [
            "id", "merchant_name", "business_category", "email",
            "phone", "razorpay_account_id", "timezone", "created_at", "updated_at",
        ]
        row_data = {col: merchant_data[col] for col in cols}
        frame = pd.DataFrame([row_data])
        _insert_frame(db, frame, "merchants")
        db.commit()
        counts["merchants"] = 1
        _log_loaded("merchants", 1)
    except Exception as exc:
        db.rollback()
        logger.error("seed.failed table=%s error=%s", "merchants", exc)
        print(f"seed.failed table=merchants error={exc}", flush=True)
        failures.append("merchants")

    for csv_name, table_name in CSV_TO_TABLE.items():
        csv_path = out / f"{csv_name}.csv"
        try:
            if not csv_path.exists():
                raise FileNotFoundError(csv_path)
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
            _insert_frame(db, frame, table_name)
            db.commit()
            counts[table_name] = len(frame)
            _log_loaded(table_name, len(frame))
        except Exception as exc:
            db.rollback()
            logger.error("seed.failed table=%s path=%s error=%s", table_name, csv_path, exc)
            print(f"seed.failed table={table_name} error={exc}", flush=True)
            failures.append(table_name)

    db.commit()
    logger.info("seed.done counts=%s failures=%s", counts, failures)
    print(f"seed.done counts={counts} failures={failures}", flush=True)
    if failures:
        raise RuntimeError(f"seed failed for tables: {', '.join(failures)}")
    return counts


def _as_text(value: object) -> str | None:
    """Normalize a cell to text so Postgres can CAST into the live column type."""
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    text_value = str(value)
    if text_value in {"", "nan", "NaT", "None", "<NA>"}:
        return None
    return text_value


def _column_types(db: Session, table_name: str) -> dict[str, str]:
    """Read live Postgres ``udt_name`` values for ``table_name`` (not ORM maps)."""
    rows = db.execute(
        text(
            """
            SELECT column_name, udt_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = :table_name
            """
        ),
        {"table_name": table_name},
    )
    return {str(name): str(udt) for name, udt in rows}


def _bind_cast(column: str, udt: str) -> str:
    """Build a CAST expression so CSV text matches the live column type."""
    bind = f":{column}"
    if udt in _INT_UDTS:
        return f"CAST(CAST({bind} AS double precision) AS {udt})"
    return f"CAST({bind} AS {udt})"


def _insert_frame(db: Session, frame: pd.DataFrame, table_name: str) -> None:
    """Insert rows with CAST into live Postgres types (no CSV/ORM map changes)."""
    if frame.empty:
        return
    prepared = frame.copy()
    for col in prepared.columns:
        prepared[col] = prepared[col].map(_as_text)
    types = _column_types(db, table_name)
    if not types:
        raise RuntimeError(f"table not found in Postgres: {table_name}")
    cols = [str(column) for column in prepared.columns if column in types]
    if not cols:
        raise RuntimeError(f"{table_name} has no columns matching Postgres")
    col_list = ", ".join(f'"{column}"' for column in cols)
    value_list = ", ".join(_bind_cast(column, types[column]) for column in cols)
    stmt = text(f'INSERT INTO "{table_name}" ({col_list}) VALUES ({value_list})')
    records = prepared[cols].to_dict(orient="records")
    conn = db.connection()
    for start in range(0, len(records), _INSERT_CHUNK):
        conn.execute(stmt, records[start : start + _INSERT_CHUNK])


def _log_loaded(table_name: str, rows: int) -> None:
    """Emit seed.loaded to the logger and stdout."""
    logger.info("seed.loaded table=%s rows=%s", table_name, rows)
    print(f"seed.loaded table={table_name} rows={rows}", flush=True)


def _open_session() -> Session:
    """Open a SQLAlchemy session against DATABASE_URL (Postgres only)."""
    url = os.environ.get("DATABASE_URL", _DEFAULT_DATABASE_URL)
    engine = create_engine(url, future=True)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    return factory()


def main() -> None:
    """CLI entry: open a DB session and run the existing seed routine."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    logger.info("seed.start")
    db: Session | None = None
    try:
        db = _open_session()
        seed_database(db)
    except Exception:
        logger.exception("seed.abort")
        sys.exit(1)
    finally:
        if db is not None:
            db.close()


if __name__ == "__main__":
    main()
