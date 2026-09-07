from decimal import Decimal

from packages.autonomy.reconciliation import (
    AutonomousTestnetReconciler,
    ExchangeSnapshot,
    ExpectedOrder,
    ObservedOrder,
    ReconciliationPolicy,
    ReconciliationStatus,
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
            raise RuntimeError("transport failure")
        return self._snapshot


def expected():
    return (ExpectedOrder("auto-1", "BTCUSDT", Decimal("1"), "FILLED"),)


def observed(status="FILLED", quantity="1", symbol="BTCUSDT"):
    return ExchangeSnapshot(
        100,
        (ObservedOrder("auto-1", symbol, Decimal(quantity), status),),
    )


def test_exact_match_is_healthy():
    reconciler = AutonomousTestnetReconciler(Provider(observed()))
    result = reconciler.reconcile(expected(), now=110)
    assert result.status is ReconciliationStatus.HEALTHY
    assert result.healthy
    assert result.recovery_action is RecoveryAction.CONTINUE


def test_missing_order_is_fail_closed():
    reconciler = AutonomousTestnetReconciler(Provider(ExchangeSnapshot(100, ())))
    result = reconciler.reconcile(expected(), now=110)
    assert result.status is ReconciliationStatus.MISMATCH
    assert not result.healthy
    assert "missing_order:auto-1" in result.reasons
    assert result.recovery_action is RecoveryAction.HALT


def test_unknown_order_is_fail_closed():
    snapshot = ExchangeSnapshot(100, (ObservedOrder("unknown", "BTCUSDT", Decimal("1"), "FILLED"),))
    result = AutonomousTestnetReconciler(Provider(snapshot)).reconcile((), now=110)
    assert result.status is ReconciliationStatus.MISMATCH
    assert "unknown_order:unknown" in result.reasons
    assert result.recovery_action is RecoveryAction.HALT


def test_quantity_symbol_and_status_mismatch_are_reported():
    result = AutonomousTestnetReconciler(Provider(observed("OPEN", "2", "ETHUSDT"))).reconcile(expected(), now=110)
    assert not result.healthy
    assert "symbol_mismatch:auto-1" in result.reasons
    assert "quantity_mismatch:auto-1" in result.reasons
    assert "status_mismatch:auto-1" in result.reasons


def test_stale_snapshot_is_fail_closed():
    reconciler = AutonomousTestnetReconciler(Provider(observed()), policy=ReconciliationPolicy(max_snapshot_age_seconds=5))
    result = reconciler.reconcile(expected(), now=110)
    assert result.status is ReconciliationStatus.STALE
    assert result.recovery_action is RecoveryAction.HALT


def test_provider_failure_is_fail_closed():
    reconciler = AutonomousTestnetReconciler(Provider(error=True))
    result = reconciler.reconcile(expected(), now=110)
    assert result.status is ReconciliationStatus.UNAVAILABLE
    assert result.recovery_action is RecoveryAction.HALT


def test_quantity_tolerance_can_allow_small_difference():
    reconciler = AutonomousTestnetReconciler(
        Provider(observed(quantity="1.0001")),
        policy=ReconciliationPolicy(quantity_tolerance=Decimal("0.001")),
    )
    result = reconciler.reconcile(expected(), now=110)
    assert result.healthy


def test_reconciliation_does_not_mutate_provider():
    provider = Provider(observed())
    reconciler = AutonomousTestnetReconciler(provider)
    reconciler.reconcile(expected(), now=110)
    assert provider.calls == 1
