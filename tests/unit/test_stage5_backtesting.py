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


def bars(closes: list[str], opens: list[str] | None = None) -> list[MarketBar]:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    opens = opens or closes
    assert len(opens) == len(closes)
    return [
        MarketBar(
            symbol="BTCUSDT",
            timeframe="1h",
            open_time=start + timedelta(hours=index),
            open=Decimal(open_price),
            high=max(Decimal(open_price), Decimal(close)),
            low=min(Decimal(open_price), Decimal(close)),
            close=Decimal(close),
            volume=Decimal("1"),
        )
        for index, (open_price, close) in enumerate(zip(opens, closes, strict=True))
    ]


def test_backtest_generates_trade_and_return() -> None:
    candles = bars(
        ["100", "106", "120", "124"],
        ["100", "105", "119", "125"],
    )
    result = BacktestEngine().run(
        candles,
        FixedSignalsStrategy([Signal.BUY, Signal.HOLD, Signal.SELL, Signal.HOLD]),
        initial_capital=Decimal("1000"),
    )

    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.entry_price == Decimal("105")
    assert trade.exit_price == Decimal("125")
    assert abs(trade.gross_pnl - Decimal("190.4761904761904761904761905")) < Decimal("1e-24")
    assert abs(result.final_equity - Decimal("1190.4761904761904761904761905")) < Decimal("1e-24")
    assert abs(result.total_return - Decimal("0.1904761904761904761904761905")) < Decimal("1e-24")
    assert result.total_fees == Decimal("0")


def test_signal_executes_on_next_candle_open() -> None:
    candles = bars(
        ["100", "110", "120"],
        ["100", "50", "200"],
    )
    result = BacktestEngine().run(
        candles,
        FixedSignalsStrategy([Signal.BUY, Signal.HOLD, Signal.HOLD]),
        initial_capital=Decimal("1000"),
    )

    assert len(result.trades) == 0
    # BUY from candle 0 executes at candle 1 open (50), then is marked at 120.
    assert result.final_equity == Decimal("2400")


def test_fees_and_slippage_reduce_result() -> None:
    candles = bars(
        ["100", "110", "120", "130"],
        ["100", "105", "115", "125"],
    )
    result = BacktestEngine().run(
        candles,
        FixedSignalsStrategy([Signal.BUY, Signal.HOLD, Signal.SELL, Signal.HOLD]),
        initial_capital=Decimal("1000"),
        fee_rate=Decimal("0.001"),
        slippage_rate=Decimal("0.001"),
    )

    assert result.total_fees > 0
    assert result.final_equity < Decimal("1200")
    assert result.trades[0].net_pnl < result.trades[0].gross_pnl


def test_open_position_is_marked_to_market_without_fake_exit() -> None:
    candles = bars(
        ["100", "110", "125"],
        ["100", "105", "120"],
    )
    result = BacktestEngine().run(
        candles,
        FixedSignalsStrategy([Signal.HOLD, Signal.BUY, Signal.HOLD]),
        initial_capital=Decimal("1000"),
    )

    assert len(result.trades) == 0
    # BUY from candle 1 executes at candle 2 open (120), so the final close is also 125.
    assert result.final_equity == Decimal("1041.666666666666666666666666")


def test_drawdown_and_win_rate_are_reported() -> None:
    candles = bars(
        ["100", "100", "120", "90", "110", "100"],
        ["100", "100", "120", "90", "110", "100"],
    )
    result = BacktestEngine().run(
        candles,
        FixedSignalsStrategy(
            [Signal.BUY, Signal.HOLD, Signal.SELL, Signal.BUY, Signal.SELL, Signal.HOLD]
        ),
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
