"""Constants for the deterministic recovery diagnosis engine."""

from __future__ import annotations

from datetime import date

DIAGNOSIS_MODEL: str = "recovery_diagnosis_v1"
DIAGNOSIS_VERSION: str = "1.0.0"

DEFAULT_TIMEZONE: str = "Asia/Kolkata"

PAYDAY_DAYS: frozenset[int] = frozenset(range(1, 6))
PRE_PAYDAY_DAYS: frozenset[int] = frozenset(range(25, 32))

# Plan billing amounts in paise used to infer subscription tier.
TIER_PREMIUM_PAISE: int = 249_900
TIER_ELITE_PAISE: int = 149_900
TIER_PRO_PAISE: int = 99_900

# Duplicate-payment window in hours.
DUPLICATE_WINDOW_HOURS: int = 48

# Salary-dependent proxy when the generator overlay is not stored in Postgres.
SALARY_DEPENDENT_SEGMENTS: frozenset[str] = frozenset({"AT_RISK", "CHURN_RISK"})

# Static 2026 Indian festival calendar (same dates as the simulator, copied
# so this package does not import simulator code).
INDIAN_FESTIVALS_2026: tuple[tuple[date, str, str], ...] = (
    (date(2026, 6, 17), "Bakrid / Eid al-Adha", "UPI congestion + festive spend"),
    (date(2026, 6, 26), "Muharram (Ashura)", "Lower banking hours in some states"),
    (date(2026, 6, 27), "Rath Yatra", "Regional UPI spike (east / coastal)"),
    (date(2026, 7, 29), "Guru Purnima", "Gift UPI volume"),
    (date(2026, 8, 15), "Independence Day", "Bank holiday + UPI timeouts"),
    (date(2026, 8, 26), "Onam (Thiruvonam)", "Kerala / south UPI spike"),
    (date(2026, 8, 28), "Raksha Bandhan", "Gift transfers, card + UPI load"),
    (date(2026, 9, 4), "Janmashtami", "Evening UPI congestion"),
)

# Primary diagnosis precedence: first listed hit wins as the single primary.
DIAGNOSIS_PRECEDENCE: tuple[str, ...] = (
    "ALREADY_PAID",
    "DUPLICATE_PAYMENT",
    "CHARGEBACK_ACTIVE",
    "CUSTOMER_CANCELLED",
    "MANDATE_REVOKED",
    "CARD_EXPIRED",
    "BANK_TIMEOUT",
    "UPI_TIMEOUT",
    "AUTHENTICATION_FAILED",
    "INSUFFICIENT_FUNDS",
    "UNKNOWN",
)

# Informational action only. Never executed by this engine.
RECOMMENDED_ACTION: dict[str, str] = {
    "ALREADY_PAID": "NO_ACTION",
    "DUPLICATE_PAYMENT": "NO_ACTION",
    "CHARGEBACK_ACTIVE": "ESCALATE_TO_AGENT",
    "CUSTOMER_CANCELLED": "STOP_RECOVERY",
    "MANDATE_REVOKED": "STOP_RECOVERY",
    "CARD_EXPIRED": "SWITCH_PAYMENT_METHOD",
    "BANK_TIMEOUT": "RETRY_PAYMENT",
    "UPI_TIMEOUT": "RETRY_PAYMENT",
    "AUTHENTICATION_FAILED": "GENERATE_PAYMENT_LINK",
    "INSUFFICIENT_FUNDS": "WAIT_FOR_PAYDAY",
    "UNKNOWN": "ESCALATE_TO_AGENT",
}

# Confidence weights for matching evidence (sum is clamped to 0..1).
CONFIDENCE_BASE: float = 0.20
CONFIDENCE_RECORDED_REASON_MATCH: float = 0.28
CONFIDENCE_OUTAGE_MATCH: float = 0.22
CONFIDENCE_HISTORY: float = 0.12
CONFIDENCE_RETRY: float = 0.08
CONFIDENCE_MANDATE: float = 0.10
CONFIDENCE_PAYDAY: float = 0.10
# Evidence item.weight is scaled by this factor when added to the raw score.
RULE_EVIDENCE_SCALE: float = 0.35

# Structured evidence codes (explainability). Not diagnosis categories.
EVIDENCE_BASE = "BASE"
EVIDENCE_NO_RULE = "NO_RULE_FIRED"
EVIDENCE_RECORDED_FAILURE_REASON = "RECORDED_FAILURE_REASON"
EVIDENCE_OUTAGE_MATCH = "OUTAGE_MATCH"
EVIDENCE_CUSTOMER_HISTORY = "CUSTOMER_HISTORY"
EVIDENCE_PAYMENT_RETRIES = "PAYMENT_RETRIES"
EVIDENCE_MANDATE_STATE = "MANDATE_STATE"
EVIDENCE_SALARY_CYCLE = "SALARY_CYCLE"
EVIDENCE_SALARY_DEPENDENT = "SALARY_DEPENDENT"
EVIDENCE_PRE_PAYDAY_WINDOW = "PRE_PAYDAY_WINDOW"
EVIDENCE_DAYS_UNTIL_PAYDAY = "DAYS_UNTIL_PAYDAY"
EVIDENCE_PRIOR_SUCCESS = "PRIOR_SUCCESS"
EVIDENCE_RECORDED_INSUFFICIENT_FUNDS = "RECORDED_INSUFFICIENT_FUNDS"

PRIORITY_HIGH_MIN: float = 70.0
PRIORITY_MEDIUM_MIN: float = 40.0

SEGMENT_PRIORITY_POINTS: dict[str, float] = {
    "HIGH_VALUE": 25.0,
    "LOYAL": 18.0,
    "AT_RISK": 16.0,
    "ACTIVE": 12.0,
    "CHURN_RISK": 10.0,
    "NEW": 8.0,
}

TIER_PRIORITY_POINTS: dict[str, float] = {
    "Premium": 10.0,
    "Elite": 8.0,
    "Pro": 5.0,
    "Starter": 2.0,
}
