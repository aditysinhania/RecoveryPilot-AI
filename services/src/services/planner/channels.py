"""Channel ranking. Never selects a policy-blocked channel."""

from __future__ import annotations

from services.planner.constants import (
    CHANNEL_COSTS_PAISE,
    CHANNEL_EFFECTIVENESS,
    NOTIFY_CHANNELS,
    POLICY_CHANNEL_NAMES,
)
from services.planner.models import ChannelPlan, PlannerStrategy
from services.policy.models import PolicyDecisionResult

_STRATEGY_PREFERRED: dict[PlannerStrategy, tuple[str, ...]] = {
    PlannerStrategy.WAIT_FOR_PAYDAY: (
        "SMS",
        "WhatsApp",
        "UPI_PAYMENT_LINK",
        "Email",
        "DASHBOARD_NOTIFICATION",
    ),
    PlannerStrategy.RETRY_PAYMENT: (
        "SMS",
        "UPI_PAYMENT_LINK",
        "WhatsApp",
        "Email",
        "DASHBOARD_NOTIFICATION",
    ),
    PlannerStrategy.RETRY_SILENTLY: ("DASHBOARD_NOTIFICATION",),
    PlannerStrategy.SEND_PAYMENT_LINK: (
        "WhatsApp",
        "UPI_PAYMENT_LINK",
        "SMS",
        "Email",
        "DASHBOARD_NOTIFICATION",
    ),
    PlannerStrategy.SWITCH_PAYMENT_METHOD: (
        "WhatsApp",
        "CARD_UPDATE_LINK",
        "SMS",
        "Email",
        "DASHBOARD_NOTIFICATION",
    ),
    PlannerStrategy.REQUEST_NEW_MANDATE: (
        "WhatsApp",
        "CARD_UPDATE_LINK",
        "Email",
        "SMS",
        "DASHBOARD_NOTIFICATION",
    ),
    PlannerStrategy.HONOUR_PROMISE_TO_PAY: (
        "WhatsApp",
        "SMS",
        "Email",
        "DASHBOARD_NOTIFICATION",
    ),
    PlannerStrategy.ESCALATE_TO_HUMAN: (
        "Voice",
        "DASHBOARD_NOTIFICATION",
        "Email",
    ),
    PlannerStrategy.STOP_RECOVERY: ("DASHBOARD_NOTIFICATION",),
}


def _blocked(policy: PolicyDecisionResult) -> set[str]:
    """Policy blocked set, plus notify channels when silent retry is required."""
    blocked = {name for name in policy.blocked_channels}
    if policy.silent_retry_allowed:
        blocked.update(NOTIFY_CHANNELS)
    return blocked


def _allowed(policy: PolicyDecisionResult, blocked: set[str]) -> set[str]:
    """Channels the planner may use. Dashboard is always permitted."""
    granted = set(policy.allowed_channels) or set(POLICY_CHANNEL_NAMES)
    granted.difference_update(blocked)
    granted.add("DASHBOARD_NOTIFICATION")
    if "WhatsApp" in granted or "SMS" in granted or "Email" in granted:
        granted.add("UPI_PAYMENT_LINK")
        granted.add("CARD_UPDATE_LINK")
    return granted


def _rank_key(name: str) -> tuple[float, int]:
    """Higher effectiveness, then lower cost."""
    effect = float(CHANNEL_EFFECTIVENESS.get(name, 0))
    cost = CHANNEL_COSTS_PAISE.get(name, 0)
    return (effect - cost / 10.0, -cost)


def plan_channels(
    strategy: PlannerStrategy,
    policy: PolicyDecisionResult,
) -> ChannelPlan:
    """Pick ranked channels that are not blocked.

    Args:
        strategy: Primary planner strategy.
        policy: Phase 5B decision (allow / block lists).

    Returns:
        Recommended channel names, total unit cost in paise, and a reason.
    """
    blocked = _blocked(policy)
    allowed = _allowed(policy, blocked)
    preferred = _STRATEGY_PREFERRED.get(strategy, ("DASHBOARD_NOTIFICATION",))
    picked: list[str] = []
    for name in preferred:
        if name in allowed and name not in picked:
            if name in POLICY_CHANNEL_NAMES and name in blocked:
                continue
            picked.append(name)
        if len(picked) >= 3:
            break
    if not picked:
        picked = ["DASHBOARD_NOTIFICATION"]
    picked.sort(key=_rank_key, reverse=True)
    # Keep dashboard last when other channels exist.
    if "DASHBOARD_NOTIFICATION" in picked and len(picked) > 1:
        picked = [n for n in picked if n != "DASHBOARD_NOTIFICATION"] + [
            "DASHBOARD_NOTIFICATION"
        ]
    cost = sum(CHANNEL_COSTS_PAISE.get(name, 0) for name in picked)
    if strategy == PlannerStrategy.RETRY_SILENTLY:
        reason = "Silent retry: no customer notify channels. Dashboard only."
        picked = ["DASHBOARD_NOTIFICATION"]
        cost = 0
    elif strategy == PlannerStrategy.STOP_RECOVERY:
        reason = "Stop plan: merchant dashboard notification only."
        picked = ["DASHBOARD_NOTIFICATION"]
        cost = 0
    else:
        blocked_list = ", ".join(sorted(blocked & POLICY_CHANNEL_NAMES)) or "none"
        reason = (
            f"Ranked by effectiveness and unit cost. Blocked by policy: {blocked_list}."
        )
    return ChannelPlan(recommended=picked, cost_paise=cost, channel_reason=reason)
