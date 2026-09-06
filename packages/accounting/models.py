from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, CheckConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.database.base import Base


class AccountingTransactionRecord(Base):
    __tablename__ = "accounting_transactions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    portfolio_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("portfolios.id", ondelete="SET NULL"), index=True)
    reference: Mapped[str] = mapped_column(String(120), unique=True)
    transaction_type: Mapped[str] = mapped_column(String(50), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, default=lambda: {})
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    entries: Mapped[list[AccountingEntryRecord]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan", order_by="AccountingEntryRecord.line_number"
    )


class AccountingEntryRecord(Base):
    __tablename__ = "accounting_entries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounting_transactions.id", ondelete="CASCADE"), index=True
    )
    line_number: Mapped[int] = mapped_column(Integer)
    account: Mapped[str] = mapped_column(String(120), index=True)
    asset: Mapped[str] = mapped_column(String(32), index=True)
    debit: Mapped[Decimal] = mapped_column(Numeric(30, 18), default=Decimal("0"))
    credit: Mapped[Decimal] = mapped_column(Numeric(30, 18), default=Decimal("0"))
    memo: Mapped[str | None] = mapped_column(Text)
    transaction: Mapped[AccountingTransactionRecord] = relationship(back_populates="entries")

    __table_args__ = (
        UniqueConstraint("transaction_id", "line_number", name="uq_accounting_entries_transaction_line"),
        CheckConstraint("debit >= 0", name="ck_accounting_entries_debit_nonnegative"),
        CheckConstraint("credit >= 0", name="ck_accounting_entries_credit_nonnegative"),
        CheckConstraint("(debit > 0 AND credit = 0) OR (credit > 0 AND debit = 0)", name="ck_accounting_entries_one_side"),
        Index("ix_accounting_entries_transaction_asset", "transaction_id", "asset"),
    )
