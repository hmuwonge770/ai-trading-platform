from decimal import Decimal

import pytest

from packages.autonomy.decision import (
    AutonomousDecisionEngine,
    DecisionAction,
    DecisionPolicy,
    MarketSnapshot,
)


def snapshot(fast: str, slow: str, rsi: str) -> MarketSnapshot:
    return MarketSnapshot(
        symbol="BTCUSDT",
        price=Decimal("100000"),
        ema_fast=Decimal(fast),
        ema_slow=Decimal(slow),
        rsi=Decimal(rsi),
        timestamp=1,
    )


def test_bullish_conditions_produce_buy() -> None:
    result = AutonomousDecisionEngine().evaluate(snapshot("101", "100", "55"))
    assert result.action is DecisionAction.BUY
    assert result.confidence == Decimal("0.80")


def test_bearish_conditions_produce_sell() -> None:
    result = AutonomousDecisionEngine().evaluate(snapshot("99", "100", "45"))
    assert result.action is DecisionAction.SELL


def test_ambiguous_conditions_hold() -> None:
    result = AutonomousDecisionEngine().evaluate(snapshot("101", "100", "80"))
    assert result.action is DecisionAction.HOLD


def test_invalid_market_snapshot_fails_closed() -> None:
    with pytest.raises(ValueError):
        snapshot("101", "100", "101")


def test_policy_rejects_invalid_confidence() -> None:
    with pytest.raises(ValueError):
        DecisionPolicy(min_confidence=Decimal("0"))
