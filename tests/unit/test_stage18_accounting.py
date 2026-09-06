from decimal import Decimal

import pytest

from packages.accounting.ledger import AccountingEntry, AccountingTransaction, Ledger, LedgerError


def transfer(reference: str = "deposit-001") -> AccountingTransaction:
    amount = Decimal("1000.25")
    return AccountingTransaction(
        reference=reference,
        transaction_type="deposit",
        entries=(
            AccountingEntry(account="ASSET:CASH", asset="USDT", debit=amount),
            AccountingEntry(account="EQUITY:OWNER", asset="USDT", credit=amount),
        ),
    )


def test_balanced_transaction_is_accepted_per_asset() -> None:
    transaction = AccountingTransaction(
        reference="trade-001",
        transaction_type="trade",
        entries=(
            AccountingEntry(account="ASSET:BTC", asset="BTC", debit=Decimal("0.01")),
            AccountingEntry(account="ASSET:CASH", asset="USDT", debit=Decimal("1000")),
            AccountingEntry(account="ASSET:BTC_SOLD", asset="BTC", credit=Decimal("0.01")),
            AccountingEntry(account="ASSET:CASH", asset="USDT", credit=Decimal("1000")),
        ),
    )
    assert len(transaction.entries) == 4


def test_unbalanced_transaction_is_rejected() -> None:
    with pytest.raises(LedgerError, match="not balanced for asset USDT"):
        AccountingTransaction(
            reference="bad-001",
            transaction_type="trade",
            entries=(
                AccountingEntry(account="ASSET:CASH", asset="USDT", debit=Decimal("100")),
                AccountingEntry(account="INCOME:FEES", asset="USDT", credit=Decimal("1")),
            ),
        )


def test_entry_must_have_exactly_one_side() -> None:
    with pytest.raises(LedgerError, match="exactly one"):
        AccountingEntry(account="ASSET:CASH", asset="USDT")
    with pytest.raises(LedgerError, match="exactly one"):
        AccountingEntry(account="ASSET:CASH", asset="USDT", debit=Decimal("1"), credit=Decimal("1"))


def test_ledger_is_idempotent_by_reference() -> None:
    ledger = Ledger()
    transaction = transfer()
    assert ledger.post(transaction) == transaction
    assert ledger.post(transaction) == transaction
    assert len(ledger.transactions) == 1


def test_ledger_rejects_same_reference_with_different_transaction() -> None:
    ledger = Ledger()
    ledger.post(transfer())
    with pytest.raises(LedgerError, match="different transaction"):
        ledger.post(transfer("deposit-001").__class__(
            reference="deposit-001",
            transaction_type="withdrawal",
            entries=(
                AccountingEntry(account="ASSET:CASH", asset="USDT", credit=Decimal("100")),
                AccountingEntry(account="EQUITY:OWNER", asset="USDT", debit=Decimal("100")),
            ),
        ))


def test_account_balance_uses_debits_minus_credits() -> None:
    ledger = Ledger()
    ledger.post(transfer())
    ledger.post(
        AccountingTransaction(
            reference="fee-001",
            transaction_type="fee",
            entries=(
                AccountingEntry(account="EXPENSE:FEES", asset="USDT", debit=Decimal("2.50")),
                AccountingEntry(account="ASSET:CASH", asset="USDT", credit=Decimal("2.50")),
            ),
        )
    )
    assert ledger.balance("ASSET:CASH", "USDT").balance == Decimal("997.75")
    assert ledger.balance("EQUITY:OWNER", "USDT").balance == Decimal("-1000.25")
