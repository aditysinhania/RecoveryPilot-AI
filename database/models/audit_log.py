"""Append-only compliance trail for recovery decisions and actions."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base, UUIDPrimaryKeyMixin
from database.models.enums import (
    ActorType,
    AuditEventType,
    PolicyDecision,
    actor_type_enum,
    audit_event_type_enum,
    policy_decision_enum,
)

if TYPE_CHECKING:
    from database.models.recovery_case import RecoveryCase


class AuditLog(UUIDPrimaryKeyMixin, Base):
    """Replayable event. JSONB payload holds diagnosis, options considered, and gate results.

    Rows are not cascade-deleted with a case so the compliance trail survives.
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_created_at", "created_at"),
        Index("ix_audit_logs_event_type", "event_type"),
        Index("ix_audit_logs_policy_decision", "policy_decision"),
        Index("ix_audit_logs_recovery_case_id", "recovery_case_id"),
        Index("ix_audit_logs_case_created", "recovery_case_id", "created_at"),
        Index(
            "ix_audit_logs_payload_gin",
            "structured_payload",
            postgresql_using="gin",
        ),
        {"comment": "Append-only audit trail. structured_payload is JSONB for GIN-friendly replay."},
    )

    recovery_case_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("recovery_cases.id", ondelete="RESTRICT"),
        nullable=True,
    )
    actor_type: Mapped[ActorType] = mapped_column(actor_type_enum, nullable=False)
    actor_name: Mapped[str] = mapped_column(String(128), nullable=False)
    event_type: Mapped[AuditEventType] = mapped_column(audit_event_type_enum, nullable=False)
    event_summary: Mapped[str] = mapped_column(String(1024), nullable=False)
    structured_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    policy_decision: Mapped[PolicyDecision | None] = mapped_column(
        policy_decision_enum,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )

    recovery_case: Mapped[RecoveryCase | None] = relationship(back_populates="audit_logs")
