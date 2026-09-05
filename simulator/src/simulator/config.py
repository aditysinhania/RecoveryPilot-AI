"""Configurable, deterministic parameters for the FitLife Gym synthetic ecosystem."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid5
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
NAMESPACE = UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")

# Plan prices in paise (₹499, ₹999, ₹1499, ₹2499).
PLAN_STARTER_PAISE = 49_900
PLAN_PRO_PAISE = 99_900
PLAN_ELITE_PAISE = 149_900
PLAN_PREMIUM_PAISE = 249_900


def deterministic_uuid(seed: int, kind: str, key: str) -> UUID:
    """Build a UUID5 so the same seed always yields the same identifiers."""
    return uuid5(NAMESPACE, f"{seed}:{kind}:{key}")


@dataclass(frozen=True)
class GeneratorConfig:
    """All knobs for the synthetic Razorpay-like dataset."""

    seed: int = 42
    timezone: str = "Asia/Kolkata"
    as_of: datetime = field(
        default_factory=lambda: datetime(2026, 9, 2, 18, 0, tzinfo=IST)
    )
    lookback_days: int = 90

    n_customers: int = 1200
    n_subscriptions: int = 1800
    n_payment_attempts: int = 5000
    n_failed_payments: int = 750
    n_recovery_cases: int = 750
    n_recovery_actions: int = 1000
    n_promises: int = 250
    n_audit_events: int = 1000
    n_webhook_events: int = 500
    webhook_duplicate_rate: float = 0.14

    merchant_name: str = "FitLife Gym"
    business_category: str = "Fitness & Wellness"
    merchant_email: str = "billing@fitlifegym.in"
    merchant_phone: str = "+918045550100"
    razorpay_account_id: str = "acc_fitlifeblr01"
    city: str = "Bangalore"
    merchant_profile: str = "gym"
    plan_brand: str = "FitLife"
    idempotency_prefix: str = "fitlife"

    enable_festival_calendar: bool = False
    enable_behaviour_persistence: bool = False

    sms_cost_paise: int = 15
    whatsapp_cost_paise: int = 80
    voice_cost_paise: int = 250

    diagnosis_model: str = "recoverypilot-rules-v1"
    diagnosis_version: str = "1.0.0"

    output_dir: Path = field(
        default_factory=lambda: Path(__file__).resolve().parents[2] / "output"
    )

    segment_weights: dict[str, float] = field(
        default_factory=lambda: {
            "HIGH_VALUE": 0.10,
            "LOYAL": 0.30,
            "ACTIVE": 0.25,
            "NEW": 0.15,
            "AT_RISK": 0.12,
            "CHURN_RISK": 0.08,
        }
    )
    plan_weights: dict[str, float] = field(
        default_factory=lambda: {
            "Starter": 0.38,
            "Pro": 0.32,
            "Elite": 0.20,
            "Premium": 0.10,
        }
    )
    plan_paise: dict[str, int] = field(
        default_factory=lambda: {
            "Starter": PLAN_STARTER_PAISE,
            "Pro": PLAN_PRO_PAISE,
            "Elite": PLAN_ELITE_PAISE,
            "Premium": PLAN_PREMIUM_PAISE,
        }
    )
    frequency_weights: dict[str, float] = field(
        default_factory=lambda: {
            "MONTHLY": 0.90,
            "QUARTERLY": 0.08,
            "YEARLY": 0.02,
        }
    )
    method_weights: dict[str, float] = field(
        default_factory=lambda: {
            "UPI": 0.62,
            "CARD": 0.22,
            "NETBANKING": 0.10,
            "WALLET": 0.06,
        }
    )
    failure_weights: dict[str, float] = field(
        default_factory=lambda: {
            "INSUFFICIENT_FUNDS": 0.45,
            "UPI_FAILURE": 0.18,
            "BANK_TIMEOUT": 0.12,
            "CARD_EXPIRED": 0.09,
            "MANDATE_REVOKED": 0.06,
            "CUSTOMER_CANCELLED": 0.04,
            "ALREADY_PAID": 0.03,
            "DISPUTE": 0.02,
            "UNKNOWN": 0.01,
        }
    )
    language_weights: dict[str, float] = field(
        default_factory=lambda: {
            "en": 0.40,
            "hi": 0.25,
            "kn": 0.20,
            "hinglish": 0.15,
        }
    )

    @property
    def merchant_id(self) -> UUID:
        """Stable merchant primary key for this seed."""
        return deterministic_uuid(self.seed, "merchant", self.razorpay_account_id)

    @property
    def window_start(self) -> datetime:
        """Inclusive start of the 90-day observation window (IST)."""
        from datetime import timedelta

        return self.as_of - timedelta(days=self.lookback_days)
