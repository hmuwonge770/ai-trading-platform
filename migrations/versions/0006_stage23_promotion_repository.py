"""stage 23 PostgreSQL promotion repository

Revision ID: 0006_stage23
Revises: 0005_stage18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_stage23"
down_revision = "0005_stage18"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "strategy_promotions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("strategy_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_stage", sa.String(32), nullable=False),
        sa.Column("to_stage", sa.String(32), nullable=False),
        sa.Column("requested_by", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("required_approvals", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("evidence_snapshot_hash", sa.String(64), nullable=False),
        sa.Column("max_capital", sa.Numeric(30, 12), nullable=False),
        sa.Column("max_position_value", sa.Numeric(30, 12), nullable=False),
        sa.Column("max_daily_loss", sa.Numeric(30, 12), nullable=False),
        sa.Column("max_orders_per_day", sa.Integer(), nullable=False),
        sa.Column("allocation_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True)),
        sa.Column("halted_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["strategy_version_id"], ["strategy_versions.id"]),
        sa.CheckConstraint("to_stage IN ('live_canary','live_limited','live')", name="ck_strategy_promotions_live_target"),
        sa.CheckConstraint(
            "max_capital > 0 AND max_position_value > 0 AND max_position_value <= max_capital "
            "AND max_daily_loss > 0 AND max_daily_loss <= max_capital AND max_orders_per_day > 0",
            name="ck_strategy_promotions_limits",
        ),
    )
    op.create_index("ix_strategy_promotions_version_status", "strategy_promotions", ["strategy_version_id", "status"])

    op.create_table(
        "promotion_approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("promotion_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("approver_id", sa.String(255), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("decision", sa.String(16), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("capital_limit", sa.Numeric(30, 12), nullable=False),
        sa.Column("evidence_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["promotion_id"], ["strategy_promotions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("promotion_id", "approver_id", name="uq_promotion_approvals_actor"),
        sa.CheckConstraint("role IN ('risk_manager','admin','operations')", name="ck_promotion_approvals_role"),
        sa.CheckConstraint("decision IN ('approve','reject')", name="ck_promotion_approvals_decision"),
    )
    op.create_index("ix_promotion_approvals_promotion", "promotion_approvals", ["promotion_id"])

    op.create_table(
        "capital_allocations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("strategy_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("environment", sa.String(32), nullable=False),
        sa.Column("max_capital", sa.Numeric(30, 12), nullable=False),
        sa.Column("max_position_value", sa.Numeric(30, 12), nullable=False),
        sa.Column("max_daily_loss", sa.Numeric(30, 12), nullable=False),
        sa.Column("max_orders_per_day", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["strategy_version_id"], ["strategy_versions.id"]),
        sa.UniqueConstraint("strategy_version_id", "environment", name="uq_capital_allocations_version_environment"),
        sa.CheckConstraint(
            "max_capital > 0 AND max_position_value > 0 AND max_position_value <= max_capital "
            "AND max_daily_loss > 0 AND max_daily_loss <= max_capital AND max_orders_per_day > 0",
            name="ck_capital_allocations_limits",
        ),
    )

    op.create_table(
        "authorization_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("promotion_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("strategy_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("strategy_fingerprint", sa.String(64), nullable=False),
        sa.Column("environment", sa.String(32), nullable=False),
        sa.Column("risk_policy_fingerprint", sa.String(64), nullable=False),
        sa.Column("evidence_snapshot_hash", sa.String(64), nullable=False),
        sa.Column("authorization_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["promotion_id"], ["strategy_promotions.id"]),
        sa.ForeignKeyConstraint(["strategy_version_id"], ["strategy_versions.id"]),
        sa.CheckConstraint("environment IN ('live_canary','live_limited','live')", name="ck_authorization_snapshots_live_environment"),
    )
    op.create_index(
        "ix_authorization_snapshots_active",
        "authorization_snapshots",
        ["strategy_version_id", "environment", "expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_authorization_snapshots_active", table_name="authorization_snapshots")
    op.drop_table("authorization_snapshots")
    op.drop_table("capital_allocations")
    op.drop_index("ix_promotion_approvals_promotion", table_name="promotion_approvals")
    op.drop_table("promotion_approvals")
    op.drop_index("ix_strategy_promotions_version_status", table_name="strategy_promotions")
    op.drop_table("strategy_promotions")
