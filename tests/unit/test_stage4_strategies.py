from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from packages.strategies.config import MovingAverageCrossoverConfig
from packages.strategies.fingerprint import strategy_fingerprint
from packages.strategies.indicators import simple_moving_average
from packages.strategies.models import MarketBar, Signal
from packages.strategies.moving_average import MovingAverageCrossoverStrategy
from packages.strategies.registry import build_strategy


def bars(closes: list[str]) -> list[MarketBar]:
    return [
        MarketBar(
            symbol="BTCUSDT",
            timeframe="1h",
            open_time=datetime(2026, 1, 1, index, tzinfo=timezone.utc),
            open=Decimal(close),
            high=Decimal(close),
            low=Decimal(close),
            close=Decimal(close),
            volume=Decimal("1"),
        )
        for index, close in enumerate(closes)
    ]


def test_sma_is_rolling_and_does_not_use_future_values() -> None:
    result = simple_moving_average([Decimal("1"), Decimal("2"), Decimal("3"), Decimal("4")], 3)
    assert result == [None, None, Decimal("2"), Decimal("3")]


def test_moving_average_crossover_emits_buy() -> None:
    strategy = MovingAverageCrossoverStrategy(
        MovingAverageCrossoverConfig(short_window=2, long_window=3)
    )
    signals = strategy.generate_signals(bars(["3", "2", "1", "3", "5"]))
    assert [signal.signal for signal in signals] == [
        Signal.HOLD,
        Signal.HOLD,
        Signal.HOLD,
        Signal.BUY,
        Signal.HOLD,
    ]
    assert signals[3].price == Decimal("3")
    assert signals[3].reason == "short_sma_crossed_above_long_sma"


def test_moving_average_crossover_emits_sell() -> None:
    strategy = MovingAverageCrossoverStrategy(
        MovingAverageCrossoverConfig(short_window=2, long_window=3)
    )
    signals = strategy.generate_signals(bars(["1", "2", "3", "1", "0"]))
    assert [signal.signal for signal in signals] == [
        Signal.HOLD,
        Signal.HOLD,
        Signal.HOLD,
        Signal.SELL,
        Signal.HOLD,
    ]
    assert signals[3].reason == "short_sma_crossed_below_long_sma"


def test_strategy_is_deterministic() -> None:
    strategy = MovingAverageCrossoverStrategy(
        MovingAverageCrossoverConfig(short_window=2, long_window=4)
    )
    candles = bars(["10", "9", "8", "7", "8", "9", "10"])
    first = strategy.generate_signals(candles)
    second = strategy.generate_signals(candles)
    assert first == second


def test_config_rejects_invalid_window_order_and_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        MovingAverageCrossoverConfig(short_window=10, long_window=5)

    with pytest.raises(ValidationError):
        MovingAverageCrossoverConfig(short_window=2, long_window=5, future_parameter=1)


def test_fingerprint_is_stable_and_changes_with_configuration() -> None:
    first = MovingAverageCrossoverConfig(short_window=5, long_window=20)
    reordered = {"long_window": 20, "short_window": 5}
    changed = MovingAverageCrossoverConfig(short_window=6, long_window=20)

    assert strategy_fingerprint("moving_average_crossover", first) == strategy_fingerprint(
        "moving_average_crossover", reordered
    )
    assert strategy_fingerprint("moving_average_crossover", first) != strategy_fingerprint(
        "moving_average_crossover", changed
    )
    assert len(strategy_fingerprint("moving_average_crossover", first)) == 64


def test_registry_builds_only_registered_strategy() -> None:
    strategy = build_strategy("moving_average_crossover", {"short_window": 5, "long_window": 20})
    assert isinstance(strategy, MovingAverageCrossoverStrategy)

    with pytest.raises(ValueError, match="unsupported strategy family"):
        build_strategy("arbitrary_python_code", {})
