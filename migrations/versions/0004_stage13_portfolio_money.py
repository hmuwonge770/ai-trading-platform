"""stage 13 portfolio and money state

Revision ID: 0004_stage13
Revises: 0003_stage11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_stage13"
down_revision = "0003_stage11"
branch_labels = None
depends_on = None


def upgrade() -> None:
    portfolio_status = sa.Enum("created", "active", "paused", "closed", name="portfolio_status")
    portfolio_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "portfolios",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("base_currency", sa.String(16), nullable=False),
        sa.Column("status", portfolio_status, nullable=False, server_default="created"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "portfolio_balances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset", sa.String(16), nullable=False),
        sa.Column("available", sa.Numeric(30, 18), nullable=False, server_default="0"),
        sa.Column("reserved", sa.Numeric(30, 18), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("portfolio_id", "asset", name="uq_portfolio_balances_portfolio_asset"),
    )
    op.create_index("ix_portfolio_balances_portfolio_id", "portfolio_balances", ["portfolio_id"])

    op.create_table(
        "portfolio_positions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("quantity", sa.Numeric(30, 18), nullable=False, server_default="0"),
        sa.Column("average_entry_price", sa.Numeric(30, 18), nullable=False, server_default="0"),
        sa.Column("realized_pnl", sa.Numeric(30, 18), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("portfolio_id", "symbol", name="uq_portfolio_positions_portfolio_symbol"),
    )
    op.create_index("ix_portfolio_positions_portfolio_id", "portfolio_positions", ["portfolio_id"])

    op.create_table(
        "portfolio_money_movements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset", sa.String(16), nullable=False),
        sa.Column("movement_type", sa.String(30), nullable=False),
        sa.Column("amount", sa.Numeric(30, 18), nullable=False),
        sa.Column("reference", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("portfolio_id", "reference", name="uq_portfolio_money_movement_reference"),
    )
    op.create_index("ix_portfolio_money_movements_portfolio_id", "portfolio_money_movements", ["portfolio_id"])


def downgrade() -> None:
    op.drop_index("ix_portfolio_money_movements_portfolio_id", table_name="portfolio_money_movements")
    op.drop_table("portfolio_money_movements")
    op.drop_index("ix_portfolio_positions_portfolio_id", table_name="portfolio_positions")
    op.drop_table("portfolio_positions")
    op.drop_index("ix_portfolio_balances_portfolio_id", table_name="portfolio_balances")
    op.drop_table("portfolio_balances")
    op.drop_table("portfolios")
    sa.Enum(name="portfolio_status").drop(op.get_bind(), checkfirst=True)
