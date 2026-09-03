"""Reusable merchant templates for the synthetic ecosystem generator.

The default ``gym`` profile is bit-identical to the original FitLife Gym config.
Other templates (SaaS, EdTech, OTT) swap plans, method mix, and optional
festival / persistence flags without touching the gym CSV schema.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
from typing import Any

from simulator.config import (
    PLAN_ELITE_PAISE,
    PLAN_PREMIUM_PAISE,
    PLAN_PRO_PAISE,
    PLAN_STARTER_PAISE,
    GeneratorConfig,
)


@dataclass(frozen=True)
class MerchantProfile:
    """Industry template that can hydrate a ``GeneratorConfig``."""

    key: str
    merchant_name: str
    business_category: str
    merchant_email: str
    merchant_phone: str
    razorpay_account_id: str
    city: str
    plan_brand: str
    idempotency_prefix: str
    plan_paise: dict[str, int]
    plan_weights: dict[str, float]
    method_weights: dict[str, float]
    frequency_weights: dict[str, float]
    segment_weights: dict[str, float]
    enable_festival_calendar: bool = False
    enable_behaviour_persistence: bool = False
    notes: str = ""


GYM = MerchantProfile(
    key="gym",
    merchant_name="FitLife Gym",
    business_category="Fitness & Wellness",
    merchant_email="billing@fitlifegym.in",
    merchant_phone="+918045550100",
    razorpay_account_id="acc_fitlifeblr01",
    city="Bangalore",
    plan_brand="FitLife",
    idempotency_prefix="fitlife",
    plan_paise={
        "Starter": PLAN_STARTER_PAISE,
        "Pro": PLAN_PRO_PAISE,
        "Elite": PLAN_ELITE_PAISE,
        "Premium": PLAN_PREMIUM_PAISE,
    },
    plan_weights={"Starter": 0.38, "Pro": 0.32, "Elite": 0.20, "Premium": 0.10},
    method_weights={"UPI": 0.62, "CARD": 0.22, "NETBANKING": 0.10, "WALLET": 0.06},
    frequency_weights={"MONTHLY": 0.90, "QUARTERLY": 0.08, "YEARLY": 0.02},
    segment_weights={
        "HIGH_VALUE": 0.10,
        "LOYAL": 0.30,
        "ACTIVE": 0.25,
        "NEW": 0.15,
        "AT_RISK": 0.12,
        "CHURN_RISK": 0.08,
    },
    enable_festival_calendar=False,
    enable_behaviour_persistence=False,
    notes="Bangalore gym. Salary-cycle NSF. Default hackathon dataset.",
)

SAAS = MerchantProfile(
    key="saas",
    merchant_name="CloudLedger",
    business_category="B2B SaaS",
    merchant_email="billing@cloudledger.in",
    merchant_phone="+918045550200",
    razorpay_account_id="acc_cloudledger01",
    city="Bangalore",
    plan_brand="CloudLedger",
    idempotency_prefix="cloudledger",
    plan_paise={
        "Starter": 99_900,
        "Pro": 249_900,
        "Elite": 499_900,
        "Premium": 999_900,
    },
    plan_weights={"Starter": 0.22, "Pro": 0.38, "Elite": 0.28, "Premium": 0.12},
    method_weights={"UPI": 0.28, "CARD": 0.48, "NETBANKING": 0.20, "WALLET": 0.04},
    frequency_weights={"MONTHLY": 0.70, "QUARTERLY": 0.18, "YEARLY": 0.12},
    segment_weights={
        "HIGH_VALUE": 0.18,
        "LOYAL": 0.34,
        "ACTIVE": 0.22,
        "NEW": 0.12,
        "AT_RISK": 0.08,
        "CHURN_RISK": 0.06,
    },
    enable_festival_calendar=False,
    enable_behaviour_persistence=True,
    notes="B2B invoicing. Card-heavy, annual plans, sticky payers.",
)

EDTECH = MerchantProfile(
    key="edtech",
    merchant_name="LearnHub Academy",
    business_category="EdTech",
    merchant_email="billing@learnhub.academy",
    merchant_phone="+918045550300",
    razorpay_account_id="acc_learnhub01",
    city="Bangalore",
    plan_brand="LearnHub",
    idempotency_prefix="learnhub",
    plan_paise={
        "Starter": 29_900,
        "Pro": 59_900,
        "Elite": 99_900,
        "Premium": 149_900,
    },
    plan_weights={"Starter": 0.42, "Pro": 0.30, "Elite": 0.18, "Premium": 0.10},
    method_weights={"UPI": 0.72, "CARD": 0.14, "NETBANKING": 0.06, "WALLET": 0.08},
    frequency_weights={"MONTHLY": 0.86, "QUARTERLY": 0.10, "YEARLY": 0.04},
    segment_weights={
        "HIGH_VALUE": 0.08,
        "LOYAL": 0.22,
        "ACTIVE": 0.28,
        "NEW": 0.22,
        "AT_RISK": 0.12,
        "CHURN_RISK": 0.08,
    },
    enable_festival_calendar=True,
    enable_behaviour_persistence=True,
    notes="Exam-season and festival UPI congestion. Parent salary cycles.",
)

OTT = MerchantProfile(
    key="ott",
    merchant_name="StreamBox",
    business_category="OTT / Media",
    merchant_email="billing@streambox.in",
    merchant_phone="+918045550400",
    razorpay_account_id="acc_streambox01",
    city="Bangalore",
    plan_brand="StreamBox",
    idempotency_prefix="streambox",
    plan_paise={
        "Starter": 14_900,
        "Pro": 19_900,
        "Elite": 49_900,
        "Premium": 64_900,
    },
    plan_weights={"Starter": 0.40, "Pro": 0.32, "Elite": 0.18, "Premium": 0.10},
    method_weights={"UPI": 0.58, "CARD": 0.16, "NETBANKING": 0.06, "WALLET": 0.20},
    frequency_weights={"MONTHLY": 0.94, "QUARTERLY": 0.05, "YEARLY": 0.01},
    segment_weights={
        "HIGH_VALUE": 0.06,
        "LOYAL": 0.20,
        "ACTIVE": 0.30,
        "NEW": 0.18,
        "AT_RISK": 0.14,
        "CHURN_RISK": 0.12,
    },
    enable_festival_calendar=True,
    enable_behaviour_persistence=True,
    notes="Low ARPU, wallet + UPI, higher churn, festival binge windows.",
)

PROFILES: dict[str, MerchantProfile] = {
    GYM.key: GYM,
    SAAS.key: SAAS,
    EDTECH.key: EDTECH,
    OTT.key: OTT,
}


def get_profile(key: str) -> MerchantProfile:
    """Return a named template. Raises ``KeyError`` for unknown keys."""
    try:
        return PROFILES[key]
    except KeyError as exc:
        known = ", ".join(sorted(PROFILES))
        raise KeyError(f"Unknown merchant profile {key!r}. Expected one of: {known}") from exc


def config_from_profile(key: str = "gym", **overrides: Any) -> GeneratorConfig:
    """Build a ``GeneratorConfig`` from a template, then apply overrides.

    ``gym`` with no overrides matches ``GeneratorConfig()`` field-for-field so
    the default FitLife CSV artefacts stay unchanged.
    """
    profile = get_profile(key)
    payload: dict[str, Any] = {
        "merchant_profile": profile.key,
        "merchant_name": profile.merchant_name,
        "business_category": profile.business_category,
        "merchant_email": profile.merchant_email,
        "merchant_phone": profile.merchant_phone,
        "razorpay_account_id": profile.razorpay_account_id,
        "city": profile.city,
        "plan_brand": profile.plan_brand,
        "idempotency_prefix": profile.idempotency_prefix,
        "plan_paise": dict(profile.plan_paise),
        "plan_weights": dict(profile.plan_weights),
        "method_weights": dict(profile.method_weights),
        "frequency_weights": dict(profile.frequency_weights),
        "segment_weights": dict(profile.segment_weights),
        "enable_festival_calendar": profile.enable_festival_calendar,
        "enable_behaviour_persistence": profile.enable_behaviour_persistence,
    }
    payload.update(overrides)
    allowed = {item.name for item in fields(GeneratorConfig)}
    filtered = {name: value for name, value in payload.items() if name in allowed}
    return replace(GeneratorConfig(), **filtered)
