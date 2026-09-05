"""Constants for the deterministic recovery policy engine."""

from __future__ import annotations

from datetime import timedelta

POLICY_VERSION: str = "recovery_policy_v1"
DEFAULT_TIMEZONE: str = "Asia/Kolkata"

# Contact window in the customer's timezone (inclusive start, exclusive end).
CONTACT_WINDOW_START_HOUR: int = 8
CONTACT_WINDOW_END_HOUR: int = 19

# Retry cooldown: at most N payment retries inside a rolling window, plus a gap.
MAX_RETRIES_IN_WINDOW: int = 3
RETRY_WINDOW: timedelta = timedelta(days=7)
MIN_RETRY_GAP: timedelta = timedelta(hours=24)

# HIGH_VALUE invoices at or above this paise amount open an escalation path.
HIGH_VALUE_THRESHOLD_PAISE: int = 149_900
HIGH_VALUE_PRIORITY_BOOST: float = 15.0
BROKEN_PROMISE_PRIORITY_BOOST: float = 10.0

CHANNELS: tuple[str, ...] = ("WhatsApp", "SMS", "Voice", "Email")

# Evaluation order. First STOP/ESCALATE in this list wins among that severity.
POLICY_PRECEDENCE: tuple[str, ...] = (
    "already_paid",
    "chargeback",
    "consent",
    "mandate",
    "promise_to_pay",
    "retry_cooldown",
    "outage",
    "dnd_contact",
    "churn_protection",
    "high_value",
)

# Numeric rank of the folded decision. Higher = more blocking.
# Distinct from ``priority_score`` (planner queue 0–100).
DECISION_PRIORITY: dict[str, int] = {
    "ALLOW": 20,
    "WAIT": 40,
    "DENY": 60,
    "ESCALATE": 80,
    "STOP": 100,
}

# Structured evidence codes (not diagnosis categories).
EVIDENCE_ALREADY_PAID = "ALREADY_PAID"
EVIDENCE_CHARGEBACK = "CHARGEBACK_ACTIVE"
EVIDENCE_CONSENT_REVOKED = "CONSENT_REVOKED"
EVIDENCE_CONSENT_PENDING = "CONSENT_PENDING"
EVIDENCE_CONSENT_CHANNEL = "CONSENT_CHANNEL_RESTRICTED"
EVIDENCE_MANDATE_REVOKED = "MANDATE_REVOKED"
EVIDENCE_MANDATE_EXPIRED = "MANDATE_EXPIRED"
EVIDENCE_PROMISE_ACTIVE = "PROMISE_ACTIVE"
EVIDENCE_PROMISE_BROKEN = "PROMISE_BROKEN"
EVIDENCE_PROMISE_FULFILLED = "PROMISE_FULFILLED"
EVIDENCE_RETRY_CAP = "RETRY_CAP"
EVIDENCE_RETRY_GAP = "RETRY_COOLDOWN"
EVIDENCE_OUTAGE = "OUTAGE_TIMEOUT"
EVIDENCE_DND = "DND_CONTACT_WINDOW"
EVIDENCE_CANCELLED = "CUSTOMER_CANCELLED"
EVIDENCE_HARDSHIP = "HARDSHIP"
EVIDENCE_HIGH_VALUE = "HIGH_VALUE_CUSTOMER"
