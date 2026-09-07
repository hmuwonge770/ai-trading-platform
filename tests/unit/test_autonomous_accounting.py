from decimal import Decimal

import pytest

from packages.autonomy.accounting import (
    AccountingPolicy,
    AccountingSnapshot,
    AccountingStatus,
    AutonomousTestnetAccountingReconciler,
    ExpectedBalance,
    ExpectedPosition,
    ObservedBalance,
    ObservedPosition,
)
from packages.autonomy.recovery import RecoveryAction


class Provider:
    def __init__(self, snapshot=None, error=False):
        self._snapshot = snapshot
        self.error = error
        self.calls = 0

    def snapshot(self):
        self.calls += 1
        if self.error:
            raise RuntimeError("provider failed")
        return self._snapshot


def snapshot(*, balances=(), positions=(), observed_at=100):
    return AccountingSnapshot(observed_at, tuple(balances), tuple(positions))


def expected_balances():
    return (ExpectedBalance("USDT", Decimal("100"), Decimal("2")), ExpectedBalance("BTC", Decimal("1")))


def expected_positions():
    return (ExpectedPosition("BTCUSDT", Decimal("0.5")),)


def test_exact_accounting_match_is_healthy():
    provider = Provider(snapshot(
        balances=(ObservedBalance("USDT", Decimal("100"), Decimal("2")), ObservedBalance("BTC", Decimal("1"))),
        positions=(ObservedPosition("BTCUSDT", Decimal("0.5")),),
    ))
    result = AutonomousTestnetAccountingReconciler(provider).reconcile(expected_balances(), expected_positions(), now=100)
    assert result.status is AccountingStatus.HEALTHY
    assert result.healthy
    assert result.reasons == ()
    assert result.recovery_action is RecoveryAction.CONTINUE


def test_missing_and_unexpected_balances_fail_closed():
    provider = Provider(snapshot(balances=(ObservedBalance("USDT", Decimal("100")),), positions=()))
    result = AutonomousTestnetAccountingReconciler(provider).reconcile(expected_balances(), expected_positions(), now=100)
    assert result.status is AccountingStatus.MISMATCH
    assert not result.healthy
    assert "missing_balance:BTC" in result.reasons
    assert "missing_position:BTCUSDT" in result.reasons

    provider = Provider(snapshot(
        balances=(ObservedBalance("USDT", Decimal("100")), ObservedBalance("BTC", Decimal("1")), ObservedBalance("ETH", Decimal("3"))),
        positions=(ObservedPosition("BTCUSDT", Decimal("0.5")), ObservedPosition("ETHUSDT", Decimal("1"))),
    ))
    result = AutonomousTestnetAccountingReconciler(provider).reconcile(expected_balances(), expected_positions(), now=100)
    assert "unexpected_balance:ETH" in result.reasons
    assert "unexpected_position:ETHUSDT" in result.reasons


def test_quantity_mismatch_is_detected():
    provider = Provider(snapshot(
        balances=(ObservedBalance("USDT", Decimal("99.9"), Decimal("2")), ObservedBalance("BTC", Decimal("1"))),
        positions=(ObservedPosition("BTCUSDT", Decimal("0.49")),),
    ))
    result = AutonomousTestnetAccountingReconciler(provider).reconcile(expected_balances(), expected_positions(), now=100)
    assert "free_balance_mismatch:USDT" in result.reasons
    assert "position_quantity_mismatch:BTCUSDT" in result.reasons


def test_tolerance_allows_small_differences():
    provider = Provider(snapshot(
        balances=(ObservedBalance("USDT", Decimal("99.999"), Decimal("2.001")), ObservedBalance("BTC", Decimal("1.001"))),
        positions=(ObservedPosition("BTCUSDT", Decimal("0.501")),),
    ))
    result = AutonomousTestnetAccountingReconciler(
        provider, policy=AccountingPolicy(quantity_tolerance=Decimal("0.001"))
    ).reconcile(expected_balances(), expected_positions(), now=100)
    assert result.healthy


def test_stale_and_future_snapshots_fail_closed():
    stale = Provider(snapshot(observed_at=50))
    result = AutonomousTestnetAccountingReconciler(stale).reconcile(expected_balances(), expected_positions(), now=100)
    assert result.status is AccountingStatus.STALE
    assert "snapshot_stale" in result.reasons

    future = Provider(snapshot(observed_at=101))
    result = AutonomousTestnetAccountingReconciler(future).reconcile(expected_balances(), expected_positions(), now=100)
    assert result.status is AccountingStatus.STALE
    assert "snapshot_from_future" in result.reasons


def test_provider_failure_is_unavailable_and_fail_closed():
    provider = Provider(error=True)
    result = AutonomousTestnetAccountingReconciler(provider).reconcile(expected_balances(), expected_positions(), now=100)
    assert result.status is AccountingStatus.UNAVAILABLE
    assert result.recovery_action in {RecoveryAction.RETRY, RecoveryAction.HALT}


def test_invalid_policy_and_expected_values_are_rejected():
    with pytest.raises(ValueError):
        AccountingPolicy(max_snapshot_age_seconds=0)
    with pytest.raises(ValueError):
        AccountingPolicy(quantity_tolerance=Decimal("-0.1"))
    with pytest.raises(ValueError):
        ExpectedBalance("USDT", Decimal("-1"))
    with pytest.raises(ValueError):
        ExpectedPosition("BTCUSDT", Decimal("-1"))


def test_reconciliation_is_read_only():
    provider = Provider(snapshot(
        balances=(ObservedBalance("USDT", Decimal("100"), Decimal("2")), ObservedBalance("BTC", Decimal("1"))),
        positions=(ObservedPosition("BTCUSDT", Decimal("0.5")),),
    ))
    reconciler = AutonomousTestnetAccountingReconciler(provider)
    reconciler.reconcile(expected_balances(), expected_positions(), now=100)
    assert provider.calls == 1
    assert reconciler.provider is provider
