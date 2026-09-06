from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from packages.strategies.config import MovingAverageCrossoverConfig
from packages.strategies.indicators import simple_moving_average
from packages.strategies.models import MarketBar, Signal, StrategySignal


class MovingAverageCrossoverStrategy:
    """Deterministic long/flat reference strategy based on SMA crossovers."""

    family = "moving_average_crossover"

    def __init__(self, config: MovingAverageCrossoverConfig) -> None:
        self.config = config

    def generate_signals(self, candles: Sequence[MarketBar]) -> list[StrategySignal]:
        if not candles:
            return []

        closes = [candle.close for candle in candles]
        short = simple_moving_average(closes, self.config.short_window)
        long = simple_moving_average(closes, self.config.long_window)
        signals: list[StrategySignal] = []

        for index, candle in enumerate(candles):
            current_short = short[index]
            current_long = long[index]
            previous_short = short[index - 1] if index > 0 else None
            previous_long = long[index - 1] if index > 0 else None

            signal = Signal.HOLD
            reason = "insufficient_history"
            if current_short is not None and current_long is not None:
                reason = "no_crossover"
                if previous_short is not None and previous_long is not None:
                    if previous_short <= previous_long and current_short > current_long:
                        signal = Signal.BUY
                        reason = "short_sma_crossed_above_long_sma"
                    elif previous_short >= previous_long and current_short < current_long:
                        signal = Signal.SELL
                        reason = "short_sma_crossed_below_long_sma"

            indicators: dict[str, str] = {}
            if current_short is not None:
                indicators["short_sma"] = str(current_short)
            if current_long is not None:
                indicators["long_sma"] = str(current_long)

            signals.append(
                StrategySignal(
                    symbol=candle.symbol,
                    timeframe=candle.timeframe,
                    open_time=candle.open_time,
                    signal=signal,
                    price=candle.close,
                    reason=reason,
                    indicators=indicators,
                )
            )

        return signals
