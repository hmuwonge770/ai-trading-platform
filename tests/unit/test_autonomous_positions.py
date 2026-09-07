from decimal import Decimal

import pytest

from packages.autonomy.positions import (
    AutonomousPositionAgent,
    ManagedPosition,
    PositionAction,
    PositionPolicy,
)


def position(price: str = "100") -> ManagedPosition:
    return ManagedPosition(
        symbol="BTCUSDT",
        quantity=Decimal("1"),
        average_entry_price=Decimal("100"),
        current_price=Decimal(price),
        opened_at=900,
    )


def test_stop_loss_requests_exit() -> None:
    decision = AutonomousPositionAgent().evaluate(position("97"), quote_timestamp=1_000, now=1_000)

    assert decision.action is PositionAction.EXIT
    assert "stop-loss" in decision.reason


def test_take_profit_requests_exit() -> None:
    decision = AutonomousPositionAgent().evaluate(position("105"), quote_timestamp=1_000, now=1_000)

    assert decision.action is PositionAction.EXIT
    assert "take-profit" in decision.reason


def test_normal_position_is_held() -> None:
    decision = AutonomousPositionAgent().evaluate(position("102"), quote_timestamp=1_000, now=1_000)

    assert decision.action is PositionAction.HOLD


def test_stale_quote_fails_closed_to_hold() -> None:
    decision = AutonomousPositionAgent().evaluate(position("95"), quote_timestamp=900, now=1_000)

    assert decision.action is PositionAction.HOLD
    assert "stale" in decision.reason


def test_future_quote_is_rejected() -> None:
    with pytest.raises(ValueError, match="future"):
        AutonomousPositionAgent().evaluate(position(), quote_timestamp=1_001, now=1_000)


def test_invalid_position_is_rejected() -> None:
    with pytest.raises(ValueError, match="quantity"):
        ManagedPosition("BTCUSDT", Decimal("0"), Decimal("100"), Decimal("100"), 900)


def test_policy_bounds_are_validated() -> None:
    with pytest.raises(ValueError, match="stop_loss_fraction"):
        PositionPolicy(stop_loss_fraction=Decimal("0"))
