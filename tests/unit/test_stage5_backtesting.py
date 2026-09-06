from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from packages.backtesting.engine import BacktestEngine
from packages.strategies.models import MarketBar, Signal, StrategySignal


class FixedSignalsStrategy:
    family = "test_fixed_signals"

    def __init__(self, signals: list[Signal]) -> None:
        self.signals = signals

    def generate_signals(self, candles: list[MarketBar]) -> list[StrategySignal]:
        return [
            StrategySignal(
                symbol=candle.symbol,
                timeframe=candle.timeframe,
                open_time=candle.open_time,
                signal=signal,
                price=candle.close,
                reason="test",
            )
            for candle, signal in zip(candles, self.signals, strict=True)
        ]


def bars(closes: list[str]) -> list[MarketBar]:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        MarketBar(
            symbol="BTCUSDT",
            timeframe="1h",
            open_time=start + timedelta(hours=index),
            open=Decimal(close),
            high=Decimal(close),
            low=Decimal(close),
            close=Decimal(close),
            volume=Decimal("1"),
        )
        for index, close in enumerate(closes)
    ]


def test_backtest_generates_trade_and_return() -> None:
    candles = bars(["100", "110", "120", "115"])
    result = BacktestEngine().run(
        candles,
        FixedSignalsStrategy([Signal.HOLD, Signal.BUY, Signal.HOLD, Signal.SELL]),
        initial_capital=Decimal("1000"),
    )

    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.entry_price == Decimal("110")
    assert trade.exit_price == Decimal("115")
    assert trade.gross_pnl == Decimal("45.45454545454545454545454545")
    assert result.final_equity == Decimal("1045.45454545454545454545454545")
    assert result.total_return == Decimal("0.04545454545454545454545454545")
    assert result.total_fees == Decimal("0")


def test_fees_and_slippage_reduce_result() -> None:
    candles = bars(["100", "110", "120"])
    result = BacktestEngine().run(
        candles,
        FixedSignalsStrategy([Signal.BUY, Signal.HOLD, Signal.SELL]),
        initial_capital=Decimal("1000"),
        fee_rate=Decimal("0.001"),
        slippage_rate=Decimal("0.001"),
    )

    assert result.total_fees > 0
    assert result.final_equity < Decimal("1200")
    assert result.trades[0].net_pnl < result.trades[0].gross_pnl


def test_open_position_is_marked_to_market_without_fake_exit() -> None:
    candles = bars(["100", "110", "125"])
    result = BacktestEngine().run(
        candles,
        FixedSignalsStrategy([Signal.HOLD, Signal.BUY, Signal.HOLD]),
        initial_capital=Decimal("1000"),
    )

    assert len(result.trades) == 0
    assert result.final_equity == Decimal("1136.363636363636363636363636")


def test_drawdown_and_win_rate_are_reported() -> None:
    candles = bars(["100", "100", "120", "90", "110"])
    result = BacktestEngine().run(
        candles,
        FixedSignalsStrategy([Signal.BUY, Signal.HOLD, Signal.SELL, Signal.BUY, Signal.SELL]),
        initial_capital=Decimal("1000"),
    )

    assert result.max_drawdown > 0
    assert result.winning_trades == 1
    assert result.losing_trades == 0
    assert result.win_rate == Decimal("1")


def test_backtest_rejects_invalid_inputs_and_unsorted_candles() -> None:
    engine = BacktestEngine()
    candles = bars(["100", "101"])

    with pytest.raises(ValueError, match="initial_capital"):
        engine.run(candles, FixedSignalsStrategy([Signal.HOLD, Signal.HOLD]), Decimal("0"))

    with pytest.raises(ValueError, match="fee_rate"):
        engine.run(candles, FixedSignalsStrategy([Signal.HOLD, Signal.HOLD]), Decimal("1000"), Decimal("1"))

    reversed_candles = list(reversed(candles))
    with pytest.raises(ValueError, match="strictly ordered"):
        engine.run(reversed_candles, FixedSignalsStrategy([Signal.HOLD, Signal.HOLD]), Decimal("1000"))


def test_empty_dataset_returns_flat_result() -> None:
    result = BacktestEngine().run([], FixedSignalsStrategy([]), Decimal("1000"))
    assert result.final_equity == Decimal("1000")
    assert result.total_return == Decimal("0")
    assert result.max_drawdown == Decimal("0")
