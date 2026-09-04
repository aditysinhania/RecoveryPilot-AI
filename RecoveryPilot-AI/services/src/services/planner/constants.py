"""Constants for the deterministic recovery planner."""

from __future__ import annotations

from datetime import timedelta

PLAN_VERSION: str = "recovery_planner_v1"
PLANNER_VERSION: str = "1.0.0"
DEFAULT_TIMEZONE: str = "Asia/Kolkata"

# Payday retry sits inside 09:00–11:00 IST. Minute 15 is the deterministic slot.
PAYDAY_RETRY_HOUR: int = 9
PAYDAY_RETRY_MINUTE: int = 15
PAYDAY_WINDOW_END_HOUR: int = 11
PAYDAY_DAYS: frozenset[int] = frozenset(range(1, 6))

# Outage silent retry: midpoint of the 30–90 minute band.
OUTAGE_RETRY_DELAY: timedelta = timedelta(minutes=60)
OUTAGE_RETRY_WINDOW: timedelta = timedelta(minutes=90)

# Promise-to-pay: act on the promised calendar date at payday-morning time.
PROMISE_HOUR: int = 9
PROMISE_MINUTE: int = 15

CONTACT_WINDOW_START_HOUR: int = 8
CONTACT_WINDOW_END_HOUR: int = 19

PLAN_TTL: timedelta = timedelta(days=7)

# Simulator unit costs (paise). Email / dashboard / links are free.
COST_SMS_PAISE: int = 15
COST_WHATSAPP_PAISE: int = 80
COST_VOICE_PAISE: int = 250
COST_EMAIL_PAISE: int = 0
COST_DASHBOARD_PAISE: int = 0
COST_UPI_LINK_PAISE: int = 0
COST_CARD_LINK_PAISE: int = 0

CHANNEL_COSTS_PAISE: dict[str, int] = {
    "SMS": COST_SMS_PAISE,
    "WhatsApp": COST_WHATSAPP_PAISE,
    "Voice": COST_VOICE_PAISE,
    "Email": COST_EMAIL_PAISE,
    "UPI_PAYMENT_LINK": COST_UPI_LINK_PAISE,
    "CARD_UPDATE_LINK": COST_CARD_LINK_PAISE,
    "DASHBOARD_NOTIFICATION": COST_DASHBOARD_PAISE,
}

# Effectiveness 0–100. Rank = effectiveness − cost_paise / 10.
CHANNEL_EFFECTIVENESS: dict[str, int] = {
    "WhatsApp": 92,
    "UPI_PAYMENT_LINK": 88,
    "CARD_UPDATE_LINK": 84,
    "SMS": 74,
    "Voice": 80,
    "Email": 55,
    "DASHBOARD_NOTIFICATION": 40,
}

NOTIFY_CHANNELS: frozenset[str] = frozenset({"SMS", "WhatsApp", "Voice", "Email"})
POLICY_CHANNEL_NAMES: frozenset[str] = frozenset({"SMS", "WhatsApp", "Voice", "Email"})

FALLBACK_STRATEGY: dict[str, str] = {
    "WAIT_FOR_PAYDAY": "SEND_PAYMENT_LINK",
    "RETRY_SILENTLY": "SWITCH_PAYMENT_METHOD",
    "REQUEST_NEW_MANDATE": "ESCALATE_TO_HUMAN",
    "SWITCH_PAYMENT_METHOD": "SEND_PAYMENT_LINK",
    "SEND_PAYMENT_LINK": "ESCALATE_TO_HUMAN",
    "RETRY_PAYMENT": "SEND_PAYMENT_LINK",
    "HONOUR_PROMISE_TO_PAY": "SEND_PAYMENT_LINK",
    "ESCALATE_TO_HUMAN": "STOP_RECOVERY",
    "STOP_RECOVERY": "STOP_RECOVERY",
}

EXPECTED_OUTCOME: dict[str, str] = {
    "WAIT_FOR_PAYDAY": "Capture after salary credit on payday morning.",
    "RETRY_PAYMENT": "Successful retry on the original rail.",
    "RETRY_SILENTLY": "Silent capture after the rail recovers.",
    "SEND_PAYMENT_LINK": "Customer completes a fresh payment link.",
    "SWITCH_PAYMENT_METHOD": "Customer pays on an alternate instrument.",
    "REQUEST_NEW_MANDATE": "Customer updates card or Autopay mandate.",
    "HONOUR_PROMISE_TO_PAY": "Customer pays on the promised date.",
    "ESCALATE_TO_HUMAN": "Human agent reviews and closes or recovers.",
    "STOP_RECOVERY": "No further recovery action.",
}

SEGMENT_PROBABILITY: dict[str, float] = {
    "HIGH_VALUE": 0.12,
    "LOYAL": 0.10,
    "ACTIVE": 0.06,
    "AT_RISK": 0.04,
    "NEW": 0.02,
    "CHURN_RISK": 0.0,
}

# Strategy-choice confidence (distinct from expected_recovery_probability).
STRATEGY_CONFIDENCE_DIAGNOSIS_WEIGHT: float = 0.35
STRATEGY_CONFIDENCE_POLICY_WEIGHT: float = 0.30
STRATEGY_CONFIDENCE_HISTORY_WEIGHT: float = 0.20
STRATEGY_CONFIDENCE_TIMING_WEIGHT: float = 0.15

# How conclusive the policy gate is for locking a strategy.
POLICY_DECISION_STRENGTH: dict[str, float] = {
    "STOP": 0.95,
    "ESCALATE": 0.88,
    "DENY": 0.85,
    "WAIT": 0.80,
    "ALLOW": 0.74,
}
