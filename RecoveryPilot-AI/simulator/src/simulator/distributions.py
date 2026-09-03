"""Weighted sampling, persona behaviour, salary-cycle and rail-outage helpers."""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Sequence, TypeVar
from uuid import UUID
from zoneinfo import ZoneInfo

import numpy as np
from faker import Faker

from simulator.config import GeneratorConfig, deterministic_uuid

T = TypeVar("T")

BANGALORE_MOBILE_PREFIXES: tuple[str, ...] = (
    "63",
    "73",
    "80",
    "81",
    "88",
    "90",
    "93",
    "96",
    "97",
    "98",
    "99",
)

INDIAN_FIRST_NAMES: tuple[str, ...] = (
    "Aarav", "Aditya", "Ananya", "Arjun", "Bhavana", "Chetan", "Deepa", "Divya",
    "Gaurav", "Harini", "Ishaan", "Kavya", "Lakshmi", "Manish", "Meera", "Nikhil",
    "Pooja", "Priya", "Rahul", "Rajesh", "Ravi", "Rohit", "Sanjay", "Shreya",
    "Sneha", "Suresh", "Varun", "Vikram", "Vishal", "Yash", "Kiran", "Naveen",
    "Swathi", "Keerthi", "Pranav", "Siddharth", "Tanvi", "Uday", "Vivek", "Zoya",
)

INDIAN_LAST_NAMES: tuple[str, ...] = (
    "Sharma", "Patel", "Reddy", "Nair", "Iyer", "Gupta", "Singh", "Kumar",
    "Rao", "Menon", "Desai", "Joshi", "Murthy", "Pillai", "Bhat", "Hegde",
    "Shetty", "Choudhury", "Das", "Verma", "Malhotra", "Kapoor", "Banerjee", "Mehta",
)


@dataclass(frozen=True)
class OutageWindow:
    """A bank or NPCI incident that forces timeout failures."""

    outage_id: str
    institution: str
    rail: str
    failure_reason: str
    started_at: datetime
    ended_at: datetime
    summary: str

    def contains(self, moment: datetime) -> bool:
        """Return True if `moment` falls inside the outage."""
        return self.started_at <= moment < self.ended_at


class SeededRNG:
    """One seed drives random, NumPy, and Faker so runs are repeatable."""

    def __init__(self, seed: int) -> None:
        self.seed = seed
        self.random = random.Random(seed)
        self.numpy = np.random.default_rng(seed)
        self._faker: Faker | None = None

    @property
    def faker(self) -> Faker:
        """Lazily construct a seeded en_IN Faker instance."""
        if self._faker is None:
            self._faker = Faker("en_IN")
            self._faker.seed_instance(self.seed)
        return self._faker

    def choice(self, items: Sequence[T]) -> T:
        """Pick one item uniformly."""
        return items[self.random.randrange(len(items))]

    def weighted(self, weights: dict[str, float]) -> str:
        """Pick a key using relative weights."""
        keys = list(weights.keys())
        values = [weights[k] for k in keys]
        return self.random.choices(keys, weights=values, k=1)[0]

    def chance(self, probability: float) -> bool:
        """Bernoulli trial with the given probability."""
        return self.random.random() < probability

    def randint(self, lo: int, hi: int) -> int:
        """Inclusive integer."""
        return self.random.randint(lo, hi)

    def gauss_clip(self, mean: float, sigma: float, lo: float, hi: float) -> float:
        """Gaussian sample clipped to `[lo, hi]`."""
        value = self.random.gauss(mean, sigma)
        return max(lo, min(hi, value))


def razorpay_id(seed: int, prefix: str, key: str) -> str:
    """Build a Razorpay-like public id (`order_`, `pay_`, `plink_`)."""
    digest = hashlib.sha256(f"{seed}:{prefix}:{key}".encode()).hexdigest()[:14]
    return f"{prefix}_{digest}"


def indian_mobile(rng: SeededRNG) -> str:
    """Return a +91 mobile that looks Bangalore-issued."""
    prefix = rng.choice(BANGALORE_MOBILE_PREFIXES)
    rest = "".join(str(rng.randint(0, 9)) for _ in range(8))
    return f"+91{prefix}{rest}"


def slug_email(full_name: str, index: int) -> str:
    """Build a Gmail-style address from an Indian name."""
    parts = "".join(ch for ch in full_name.lower() if ch.isalpha() or ch.isspace()).split()
    handle = ".".join(parts[:2]) if parts else "member"
    return f"{handle}.{index}@gmail.com"


def is_weekend(moment: datetime, tz: ZoneInfo) -> bool:
    """Saturday/Sunday in the merchant timezone."""
    local = moment.astimezone(tz)
    return local.weekday() >= 5


def calendar_day(moment: datetime, tz: ZoneInfo) -> int:
    """Day of month in the merchant timezone."""
    return moment.astimezone(tz).day


def salary_nsf_bias(day: int) -> float:
    """Multiplier on insufficient-funds likelihood (late month is worse)."""
    if 25 <= day <= 31:
        return 1.8
    if 1 <= day <= 5:
        return 0.45
    return 1.0


def payday_recovery_boost(day: int) -> float:
    """How strongly a salary-dependent retry should succeed on this calendar day."""
    if 1 <= day <= 5:
        return 0.92
    if 6 <= day <= 10:
        return 0.55
    return 0.18


def is_salary_dependent(segment: str, rng: SeededRNG) -> bool:
    """Overlay persona: fails before payday, recovers after credit."""
    rates = {
        "HIGH_VALUE": 0.05,
        "LOYAL": 0.08,
        "ACTIVE": 0.28,
        "NEW": 0.22,
        "AT_RISK": 0.78,
        "CHURN_RISK": 0.40,
    }
    return rng.chance(rates.get(segment, 0.2))


def plan_for_segment(segment: str, cfg: GeneratorConfig, rng: SeededRNG) -> str:
    """Shift plan mix toward premium for high-value members."""
    if segment == "HIGH_VALUE":
        weights = {"Starter": 0.02, "Pro": 0.18, "Elite": 0.40, "Premium": 0.40}
    elif segment == "LOYAL":
        weights = {"Starter": 0.15, "Pro": 0.45, "Elite": 0.28, "Premium": 0.12}
    elif segment == "NEW":
        weights = {"Starter": 0.62, "Pro": 0.28, "Elite": 0.08, "Premium": 0.02}
    elif segment == "CHURN_RISK":
        weights = {"Starter": 0.50, "Pro": 0.35, "Elite": 0.12, "Premium": 0.03}
    else:
        weights = cfg.plan_weights
    return rng.weighted(weights)


def method_for_segment(segment: str, cfg: GeneratorConfig, rng: SeededRNG) -> str:
    """UPI-heavy India mix, with cards more common on premium personas."""
    if segment == "HIGH_VALUE":
        weights = {"UPI": 0.40, "CARD": 0.42, "NETBANKING": 0.12, "WALLET": 0.06}
    elif segment == "NEW":
        weights = {"UPI": 0.70, "CARD": 0.18, "NETBANKING": 0.06, "WALLET": 0.06}
    else:
        weights = cfg.method_weights
    return rng.weighted(weights)


def mandate_for_segment(segment: str, rng: SeededRNG) -> str:
    """Mandate state prior to the latest invoice."""
    if segment == "CHURN_RISK":
        return rng.weighted({"ACTIVE": 0.45, "REVOKED": 0.30, "PAUSED": 0.15, "EXPIRED": 0.10})
    if segment == "NEW":
        return rng.weighted({"ACTIVE": 0.70, "PENDING": 0.20, "PAUSED": 0.05, "EXPIRED": 0.05})
    if segment == "AT_RISK":
        return rng.weighted({"ACTIVE": 0.75, "PAUSED": 0.15, "REVOKED": 0.05, "EXPIRED": 0.05})
    return rng.weighted({"ACTIVE": 0.88, "PAUSED": 0.07, "REVOKED": 0.03, "EXPIRED": 0.02})


def build_outages(cfg: GeneratorConfig, rng: SeededRNG) -> list[OutageWindow]:
    """Place a handful of SBI/HDFC/NPCI/Axis incidents inside the 90-day window."""
    templates: tuple[tuple[str, str, str, str], ...] = (
        ("SBI", "NETBANKING", "BANK_TIMEOUT", "SBI scheduled CBS maintenance"),
        ("HDFC", "CARD", "BANK_TIMEOUT", "HDFC acquiring latency spike"),
        ("NPCI", "UPI", "UPI_FAILURE", "NPCI UPI switch timeout"),
        ("Axis Bank", "NETBANKING", "BANK_TIMEOUT", "Axis Bank IMPS/UPI downtime"),
        ("NPCI", "UPI", "UPI_FAILURE", "NPCI regional UPI degradation"),
        ("SBI", "UPI", "UPI_FAILURE", "SBI UPI collect gateway errors"),
    )
    windows: list[OutageWindow] = []
    span_hours = cfg.lookback_days * 24
    for i, (institution, rail, reason, summary) in enumerate(templates):
        offset_h = rng.randint(12, max(13, span_hours - 48))
        duration_h = rng.randint(3, 14)
        start = cfg.window_start + timedelta(hours=offset_h)
        end = start + timedelta(hours=duration_h)
        if end > cfg.as_of:
            end = cfg.as_of
        windows.append(
            OutageWindow(
                outage_id=str(deterministic_uuid(cfg.seed, "outage", str(i))),
                institution=institution,
                rail=rail,
                failure_reason=reason,
                started_at=start,
                ended_at=end,
                summary=summary,
            )
        )
    return windows


def matching_outage(
    moment: datetime,
    method: str,
    outages: Sequence[OutageWindow],
) -> OutageWindow | None:
    """Return the first outage that covers this payment rail at `moment`."""
    rail = {
        "UPI": "UPI",
        "CARD": "CARD",
        "NETBANKING": "NETBANKING",
        "WALLET": "UPI",
        "MANDATE": "UPI",
    }.get(method, "UPI")
    for outage in outages:
        if outage.contains(moment) and outage.rail == rail:
            return outage
    return None


def indian_name(rng: SeededRNG) -> str:
    """Indian full name. Faker is used when already warmed; otherwise a local table."""
    if rng._faker is not None:
        return rng.faker.name()
    return f"{rng.choice(INDIAN_FIRST_NAMES)} {rng.choice(INDIAN_LAST_NAMES)}"


def customer_uuid(cfg: GeneratorConfig, index: int) -> UUID:
    """Stable customer id."""
    return deterministic_uuid(cfg.seed, "customer", str(index))


# Indian public / festival dates overlapping a typical Jun–Sep observation window.
# Kept as a static table so festival mode needs no extra RNG.
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


def festival_on(moment: datetime, tz: ZoneInfo) -> tuple[date, str, str] | None:
    """Return the festival tuple if `moment` falls on a listed calendar day."""
    local_day = moment.astimezone(tz).date()
    for fest_date, name, effect in INDIAN_FESTIVALS_2026:
        if fest_date == local_day:
            return fest_date, name, effect
    return None


def apply_festival_failure_bias(
    weights: dict[str, float],
    moment: datetime,
    tz: ZoneInfo,
    enabled: bool,
) -> dict[str, float]:
    """Raise timeout / NSF weights on festival days. No-op when disabled."""
    if not enabled or festival_on(moment, tz) is None:
        return weights
    biased = dict(weights)
    biased["UPI_FAILURE"] = biased.get("UPI_FAILURE", 0.0) * 1.65
    biased["BANK_TIMEOUT"] = biased.get("BANK_TIMEOUT", 0.0) * 1.40
    biased["INSUFFICIENT_FUNDS"] = biased.get("INSUFFICIENT_FUNDS", 0.0) * 1.15
    return biased


def latent_pay_discipline(customer_id: str, segment: str) -> float:
    """Sticky 0–1 reliability derived from id (no RNG) so streaks are stable."""
    digest = hashlib.sha256(f"discipline:{customer_id}".encode()).hexdigest()
    noise = int(digest[:8], 16) / 0xFFFFFFFF
    base = {
        "HIGH_VALUE": 0.88,
        "LOYAL": 0.80,
        "ACTIVE": 0.68,
        "NEW": 0.58,
        "AT_RISK": 0.38,
        "CHURN_RISK": 0.28,
    }.get(segment, 0.60)
    return round(0.05 + 0.9 * (0.7 * base + 0.3 * noise), 4)


def cluster_failures_for_persistence(
    candidates: list[dict[str, Any]],
    _n_failed: int,
) -> list[dict[str, Any]]:
    """Re-rank shuffled candidates so the same customers fail across invoices.

    The input order is the already-shuffled main-RNG order. Re-ranking uses only
    hashes and due dates, so it does not consume extra random draws.
    """
    from collections import defaultdict

    by_customer: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in candidates:
        by_customer[str(row["customer_id"])].append(row)
    for rows in by_customer.values():
        rows.sort(key=lambda item: str(item["created_at"]))

    ranked_customers = sorted(
        by_customer.keys(),
        key=lambda cid: (
            latent_pay_discipline(cid, str(by_customer[cid][0].get("segment", "ACTIVE"))),
            cid,
        ),
    )
    clustered: list[dict[str, Any]] = []
    for cid in ranked_customers:
        clustered.extend(by_customer[cid])
    return clustered
