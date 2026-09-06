from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4


class LedgerError(ValueError):
    """Raised when an accounting transaction violates ledger invariants."""


@dataclass(frozen=True, slots=True)
class AccountingEntry:
    account: str
    asset: str
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")
    memo: str = ""

    def __post_init__(self) -> None:
        if not self.account.strip():
            raise LedgerError("account must not be empty")
        if not self.asset.strip():
            raise LedgerError("asset must not be empty")
        if self.debit < 0 or self.credit < 0:
            raise LedgerError("debit and credit must not be negative")
        if (self.debit > 0) == (self.credit > 0):
            raise LedgerError("an entry must have exactly one positive debit or credit")


@dataclass(frozen=True, slots=True)
class AccountingTransaction:
    transaction_id: UUID = field(default_factory=uuid4)
    reference: str = ""
    transaction_type: str = ""
    entries: tuple[AccountingEntry, ...] = ()
    occurred_at: datetime | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.reference.strip():
            raise LedgerError("reference must not be empty")
        if not self.transaction_type.strip():
            raise LedgerError("transaction_type must not be empty")
        if len(self.entries) < 2:
            raise LedgerError("an accounting transaction requires at least two entries")
        totals: dict[str, tuple[Decimal, Decimal]] = defaultdict(lambda: (Decimal("0"), Decimal("0")))
        for entry in self.entries:
            debit, credit = totals[entry.asset.upper()]
            totals[entry.asset.upper()] = (debit + entry.debit, credit + entry.credit)
        for asset, (debit, credit) in totals.items():
            if debit != credit:
                raise LedgerError(f"transaction is not balanced for asset {asset}")


@dataclass(frozen=True, slots=True)
class AccountBalance:
    account: str
    asset: str
    balance: Decimal


class Ledger:
    """In-memory immutable transaction journal used as the accounting domain boundary.

    Transactions are append-only and idempotent by reference. The persistence
    layer introduced with Stage 18 stores the same transaction and entry shape.
    """

    def __init__(self) -> None:
        self._transactions: dict[str, AccountingTransaction] = {}

    @property
    def transactions(self) -> tuple[AccountingTransaction, ...]:
        return tuple(self._transactions.values())

    def post(self, transaction: AccountingTransaction) -> AccountingTransaction:
        existing = self._transactions.get(transaction.reference)
        if existing is not None:
            if existing != transaction:
                raise LedgerError("reference already exists with a different transaction")
            return existing
        self._transactions[transaction.reference] = transaction
        return transaction

    def balance(self, account: str, asset: str) -> AccountBalance:
        if not account.strip() or not asset.strip():
            raise LedgerError("account and asset must not be empty")
        total = Decimal("0")
        normalized_asset = asset.upper()
        for transaction in self._transactions.values():
            for entry in transaction.entries:
                if entry.account == account and entry.asset.upper() == normalized_asset:
                    total += entry.debit - entry.credit
        return AccountBalance(account=account, asset=asset, balance=total)

    def balances(self) -> tuple[AccountBalance, ...]:
        totals: dict[tuple[str, str], Decimal] = defaultdict(lambda: Decimal("0"))
        for transaction in self._transactions.values():
            for entry in transaction.entries:
                key = (entry.account, entry.asset.upper())
                totals[key] += entry.debit - entry.credit
        return tuple(
            AccountBalance(account=account, asset=asset, balance=balance)
            for (account, asset), balance in sorted(totals.items())
        )
