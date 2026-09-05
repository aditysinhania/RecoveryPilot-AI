"""Create merchant_users, auth_sessions, and merchant_settings.

Revision ID: 20260905_0001
Revises:
Create Date: 2026-09-05
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

revision: str = "20260905_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add SaaS identity tables if they are missing."""
    bind = op.get_bind()
    existing = set(inspect(bind).get_table_names())
    merchants_exist = "merchants" in existing

    if "merchant_users" not in existing:
        columns = [
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("email", sa.String(length=320), nullable=False),
            sa.Column("password_hash", sa.String(length=255), nullable=False),
            sa.Column("full_name", sa.String(length=255), nullable=False),
            sa.Column("role", sa.String(length=32), nullable=False, server_default="owner"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("merchant_id", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        ]
        fks = []
        if merchants_exist:
            fks.append(
                sa.ForeignKeyConstraint(
                    ["merchant_id"],
                    ["merchants.id"],
                    name="fk_merchant_users_merchant_id_merchants",
                    ondelete="SET NULL",
                )
            )
        op.create_table(
            "merchant_users",
            *columns,
            sa.UniqueConstraint("email", name="uq_merchant_users_email"),
            *fks,
        )
        op.create_index("ix_merchant_users_merchant_id", "merchant_users", ["merchant_id"])

    if "auth_sessions" not in existing:
        op.create_table(
            "auth_sessions",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
            sa.Column("refresh_token_hash", sa.String(length=64), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("user_agent", sa.String(length=512), nullable=True),
            sa.Column("ip_address", sa.String(length=64), nullable=True),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["merchant_users.id"],
                name="fk_auth_sessions_user_id_merchant_users",
                ondelete="CASCADE",
            ),
            sa.UniqueConstraint("refresh_token_hash", name="uq_auth_sessions_refresh_token_hash"),
        )
        op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
        op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"])

    if "merchant_settings" not in existing and merchants_exist:
        op.create_table(
            "merchant_settings",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("merchant_id", sa.Uuid(as_uuid=True), nullable=False),
            sa.Column("onboarding_step", sa.Integer(), nullable=False, server_default="1"),
            sa.Column(
                "onboarding_completed",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
            sa.Column(
                "onboarding_completed_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
            sa.Column(
                "workspace_kind",
                sa.String(length=16),
                nullable=False,
                server_default="none",
            ),
            sa.Column("razorpay_key_id", sa.String(length=128), nullable=True),
            sa.Column("razorpay_key_secret", sa.String(length=255), nullable=True),
            sa.Column("razorpay_webhook_secret", sa.String(length=255), nullable=True),
            sa.Column("gemini_api_key", sa.String(length=255), nullable=True),
            sa.Column("gemini_model", sa.String(length=128), nullable=True),
            sa.Column(
                "notify_email_recovery",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            ),
            sa.Column(
                "notify_email_digest",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            ),
            sa.Column(
                "notify_webhook_failures",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            ),
            sa.ForeignKeyConstraint(
                ["merchant_id"],
                ["merchants.id"],
                name="fk_merchant_settings_merchant_id_merchants",
                ondelete="CASCADE",
            ),
            sa.UniqueConstraint("merchant_id", name="uq_merchant_settings_merchant_id"),
        )


def downgrade() -> None:
    """Drop SaaS identity tables."""
    op.drop_table("merchant_settings")
    op.drop_table("auth_sessions")
    op.drop_table("merchant_users")
