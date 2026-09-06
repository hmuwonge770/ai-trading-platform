from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from packages.strategies.models import MarketBar, Signal, StrategySignal
from packages.trading.paper import PaperTradingConfig, PaperTradingEngine


class FixedSignalStrategy:
    family = "paper-test"

    def __init__(self, signals: list[Signal]) -> None:
        self.signals = signals

    def generate_signals(self, candles: list[MarketBar]) -> list[StrategySignal]:
        return [
            StrategySignal(
                symbol=candle.symbol,
                timeframe=candle.timeframe,
                open_time=candle.open_time,
                signal=self.signals[min(index, len(self.signals) - 1)],
                price=candle.close,
                reason="test signal",
            )
            for index, candle in enumerate(candles)
        ]


def make_candles(count: int = 5) -> list[MarketBar]:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        MarketBar(
            symbol="BTCUSDT",
            timeframe="1m",
            open_time=start + timedelta(minutes=index),
            open=Decimal(100 + index),
            high=Decimal(101 + index),
            low=Decimal(99 + index),
            close=Decimal("100.5") + index,
            volume=Decimal("10"),
        )
        for index in range(count)
    ]


def test_warmup_does_not_execute_historical_signals() -> None:
    engine = PaperTradingEngine(
        PaperTradingConfig(initial_cash=Decimal("1000"), order_quantity=Decimal("2"), warmup_candles=3)
    )
    strategy = FixedSignalStrategy([Signal.BUY, Signal.BUY, Signal.BUY])

    engine.start(make_candles(3), strategy, "strategy-v1")

    assert engine.position_quantity == Decimal("0")
    assert engine.cash == Decimal("1000")
    assert engine.pending_signal is None


def test_signal_executes_on_next_candle_open_with_fee_and_slippage() -> None:
    candles = make_candles(4)
    engine = PaperTradingEngine(
        PaperTradingConfig(
            initial_cash=Decimal("1000"),
            order_quantity=Decimal("2"),
            fee_rate=Decimal("0.001"),
            slippage_rate=Decimal("0.01"),
            warmup_candles=2,
        )
    )
    strategy = FixedSignalStrategy([Signal.HOLD, Signal.HOLD, Signal.BUY, Signal.SELL])
    engine.start(candles[:2], strategy, "strategy-v1")

    signal_result = engine.on_candle(candles[2], strategy)
    fill_result = engine.on_candle(candles[3], strategy)

    assert signal_result.signal.side == Signal.BUY
    assert signal_result.fill is None
    assert fill_result.signal.side == Signal.SELL
    assert fill_result.order is not None
    assert fill_result.fill is not None
    assert fill_result.fill.side == Signal.BUY
    assert fill_result.fill.price == Decimal("104.03")
    assert fill_result.fill.fee == Decimal("0.20806")
    assert engine.position_quantity == Decimal("2")
    assert engine.cash == Decimal("791.73194")


def test_buy_then_sell_are_executed_on_following_candles() -> None:
    candles = make_candles(4)
    engine = PaperTradingEngine(
        PaperTradingConfig(initial_cash=Decimal("1000"), order_quantity=Decimal("2"), warmup_candles=1)
    )
    strategy = FixedSignalStrategy([Signal.HOLD, Signal.BUY, Signal.SELL, Signal.HOLD])
    engine.start(candles[:1], strategy, "strategy-v1")

    buy_signal = engine.on_candle(candles[1], strategy)
    sell_result = engine.on_candle(candles[2], strategy)

    assert buy_signal.fill is None
    assert sell_result.fill is not None
    assert sell_result.fill.side == Signal.BUY
    assert engine.position_quantity == Decimal("2")
    assert engine.cash == Decimal("796")

    close_result = engine.on_candle(candles[3], strategy)
    assert close_result.fill is not None
    assert close_result.fill.side == Signal.SELL
    assert engine.position_quantity == Decimal("0")
    assert engine.cash == Decimal("1002")


def test_strategy_must_return_one_signal_per_candle() -> None:
    class InvalidStrategy:
        family = "invalid"

        def generate_signals(self, candles: list[MarketBar]) -> list[StrategySignal]:
            return []

    engine = PaperTradingEngine(
        PaperTradingConfig(initial_cash=Decimal("1000"), order_quantity=Decimal("1"), warmup_candles=1)
    )
    candles = make_candles(2)
    engine.start(candles[:1], FixedSignalStrategy([Signal.HOLD]), "strategy-v1")

    with pytest.raises(ValueError, match="exactly one signal"):
        engine.on_candle(candles[1], InvalidStrategy())


def test_paper_engine_rejects_out_of_order_live_candles() -> None:
    engine = PaperTradingEngine(
        PaperTradingConfig(initial_cash=Decimal("1000"), order_quantity=Decimal("1"), warmup_candles=2)
    )
    strategy = FixedSignalStrategy([Signal.HOLD])
    candles = make_candles(3)
    engine.start(candles[:2], strategy, "strategy-v1")

    with pytest.raises(ValueError, match="strictly ordered"):
        engine.on_candle(candles[1], strategy)


def test_insufficient_cash_does_not_create_a_paper_fill() -> None:
    candles = make_candles(2)
    engine = PaperTradingEngine(
        PaperTradingConfig(initial_cash=Decimal("100"), order_quantity=Decimal("2"), warmup_candles=1)
    )
    strategy = FixedSignalStrategy([Signal.HOLD, Signal.BUY])
    engine.start(candles[:1], strategy, "strategy-v1")

    result = engine.on_candle(candles[1], strategy)

    assert result.fill is None
    assert result.order is None
    assert engine.position_quantity == Decimal("0")
    assert engine.cash == Decimal("100")
