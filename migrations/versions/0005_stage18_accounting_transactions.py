"""stage 18 accounting transactions

Revision ID: 0005_stage18
Revises: 0004_stage13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_stage18"
down_revision = "0004_stage13"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "accounting_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reference", sa.String(120), nullable=False),
        sa.Column("transaction_type", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("reference", name="uq_accounting_transactions_reference"),
    )
    op.create_index("ix_accounting_transactions_portfolio_id", "accounting_transactions", ["portfolio_id"])
    op.create_index("ix_accounting_transactions_transaction_type", "accounting_transactions", ["transaction_type"])
    op.create_index("ix_accounting_transactions_occurred_at", "accounting_transactions", ["occurred_at"])

    op.create_table(
        "accounting_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("account", sa.String(120), nullable=False),
        sa.Column("asset", sa.String(32), nullable=False),
        sa.Column("debit", sa.Numeric(30, 18), nullable=False, server_default="0"),
        sa.Column("credit", sa.Numeric(30, 18), nullable=False, server_default="0"),
        sa.Column("memo", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["transaction_id"], ["accounting_transactions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("transaction_id", "line_number", name="uq_accounting_entries_transaction_line"),
        sa.CheckConstraint("debit >= 0", name="ck_accounting_entries_debit_nonnegative"),
        sa.CheckConstraint("credit >= 0", name="ck_accounting_entries_credit_nonnegative"),
        sa.CheckConstraint(
            "(debit > 0 AND credit = 0) OR (credit > 0 AND debit = 0)",
            name="ck_accounting_entries_one_side",
        ),
    )
    op.create_index("ix_accounting_entries_transaction_id", "accounting_entries", ["transaction_id"])
    op.create_index("ix_accounting_entries_account", "accounting_entries", ["account"])
    op.create_index("ix_accounting_entries_asset", "accounting_entries", ["asset"])
    op.create_index(
        "ix_accounting_entries_transaction_asset",
        "accounting_entries",
        ["transaction_id", "asset"],
    )


def downgrade() -> None:
    op.drop_index("ix_accounting_entries_transaction_asset", table_name="accounting_entries")
    op.drop_index("ix_accounting_entries_asset", table_name="accounting_entries")
    op.drop_index("ix_accounting_entries_account", table_name="accounting_entries")
    op.drop_index("ix_accounting_entries_transaction_id", table_name="accounting_entries")
    op.drop_table("accounting_entries")
    op.drop_index("ix_accounting_transactions_occurred_at", table_name="accounting_transactions")
    op.drop_index("ix_accounting_transactions_transaction_type", table_name="accounting_transactions")
    op.drop_index("ix_accounting_transactions_portfolio_id", table_name="accounting_transactions")
    op.drop_table("accounting_transactions")
