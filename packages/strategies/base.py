from __future__ import annotations

from typing import Protocol, Sequence

from packages.strategies.models import MarketBar, StrategySignal


class Strategy(Protocol):
    """Deterministic strategy contract used by backtesting and paper trading."""

    family: str

    def generate_signals(self, candles: Sequence[MarketBar]) -> list[StrategySignal]:
        """Generate one signal per completed candle using only current/past data."""
        ...
