from decimal import Decimal

import pytest

from packages.autonomy.performance import (
    AutonomousTestnetPerformanceMonitor,
    ExecutionObservation,
    PerformancePolicy,
    PerformanceStatus,
)


def observation(fill_price="100", filled_quantity="1") -> ExecutionObservation:
    return ExecutionObservation(
        order_id="order-1", symbol="BTCUSDT",
        expected_price=Decimal("100"), fill_price=Decimal(fill_price),
        expected_quantity=Decimal("1"), filled_quantity=Decimal(filled_quantity),
        submitted_at=100, completed_at=101,
    )


def test_exact_execution_is_healthy() -> None:
    report = AutonomousTestnetPerformanceMonitor().assess((observation(),))
    assert report.status is PerformanceStatus.HEALTHY
    assert report.average_slippage_bps == Decimal("0")
    assert report.fill_rate == Decimal("1")


def test_slippage_is_attributed_and_reviewed() -> None:
    report = AutonomousTestnetPerformanceMonitor(
        policy=PerformancePolicy(max_slippage_bps=Decimal("10"))
    ).assess((observation("100.20"),))
    assert report.status is PerformanceStatus.REVIEW
    assert "slippage_limit_exceeded" in report.reasons
    assert report.max_slippage_bps == Decimal("20")


def test_fill_shortfall_is_reviewed() -> None:
    report = AutonomousTestnetPerformanceMonitor(
        policy=PerformancePolicy(max_fill_shortfall_ratio=Decimal("0.10"))
    ).assess((observation(filled_quantity="0.8"),))
    assert report.status is PerformanceStatus.REVIEW
    assert "fill_rate_limit_exceeded" in report.reasons


def test_no_observations_are_unavailable() -> None:
    report = AutonomousTestnetPerformanceMonitor().assess(())
    assert report.status is PerformanceStatus.UNAVAILABLE
    assert report.reasons == ("no_observations",)


def test_invalid_observation_is_rejected() -> None:
    with pytest.raises(ValueError):
        observation(fill_price="0")
