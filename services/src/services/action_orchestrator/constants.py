"""Action orchestrator constants. Display statuses map onto existing ExecutionStatus."""

from __future__ import annotations

ORCHESTRATOR_VERSION: str = "recovery_orchestrator_v1"
ACTOR_NAME: str = "ACTION_ORCHESTRATOR"

DISPLAY_SCHEDULED: str = "SCHEDULED"
DISPLAY_SENT: str = "SENT"
DISPLAY_SUCCESS: str = "SUCCESS"
DISPLAY_FAILED: str = "FAILED"
DISPLAY_CANCELLED: str = "CANCELLED"
DISPLAY_EXPIRED: str = "EXPIRED"
DISPLAY_RETRYING: str = "RETRYING"

CHIP_SCHEDULED: str = "Scheduled"
CHIP_LINK_SENT: str = "Link Sent"
CHIP_RETRYING: str = "Retrying"
CHIP_DELIVERED: str = "Delivered"
CHIP_FAILED: str = "Failed"

TERMINAL_DISPLAY: frozenset[str] = frozenset(
    {DISPLAY_SUCCESS, DISPLAY_CANCELLED, DISPLAY_EXPIRED}
)
