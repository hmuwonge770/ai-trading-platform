from decimal import Decimal

import pytest

from packages.autonomy.position_recovery import (
    AutonomousPositionRecovery,
    ExpectedPosition,
    ObservedPosition,
    PositionRecoveryAction,
    PositionRecoveryStatus,
)


def _expected(symbol: str = "BTCUSDT", quantity: str = "1") -> tuple[ExpectedPosition, ...]:
    return (ExpectedPosition(symbol, Decimal(quantity)),)


def _observed(symbol: str = "BTCUSDT", quantity: str = "1") -> tuple[ObservedPosition, ...]:
    return (ObservedPosition(symbol, Decimal(quantity)),)


def test_matching_position_is_healthy() -> None:
    report = AutonomousPositionRecovery().assess(_expected(), _observed(), observed_at=100, now=110)
    assert report.status is PositionRecoveryStatus.MATCHED
    assert report.action is PositionRecoveryAction.CONTINUE
    assert report.healthy is True


def test_missing_position_halts() -> None:
    report = AutonomousPositionRecovery().assess(_expected(), (), observed_at=100, now=110)
    assert report.status is PositionRecoveryStatus.MISSING
    assert report.action is PositionRecoveryAction.HALT
    assert report.healthy is False


def test_orphaned_position_halts() -> None:
    report = AutonomousPositionRecovery().assess((), _observed(), observed_at=100, now=110)
    assert report.status is PositionRecoveryStatus.ORPHANED
    assert report.action is PositionRecoveryAction.HALT


def test_quantity_mismatch_halts() -> None:
    report = AutonomousPositionRecovery().assess(_expected(quantity="1"), _observed(quantity="2"), observed_at=100, now=110)
    assert report.status is PositionRecoveryStatus.QUANTITY_MISMATCH
    assert report.action is PositionRecoveryAction.HALT


def test_stale_snapshot_halts() -> None:
    report = AutonomousPositionRecovery().assess(_expected(), _observed(), observed_at=1, now=40)
    assert report.status is PositionRecoveryStatus.STALE
    assert report.action is PositionRecoveryAction.HALT


def test_future_snapshot_halts() -> None:
    report = AutonomousPositionRecovery().assess(_expected(), _observed(), observed_at=200, now=100)
    assert report.status is PositionRecoveryStatus.STALE
    assert report.action is PositionRecoveryAction.HALT


def test_invalid_position_is_rejected() -> None:
    with pytest.raises(ValueError):
        ExpectedPosition("", Decimal("1"))
    with pytest.raises(ValueError):
        ObservedPosition("BTCUSDT", Decimal("-1"))
