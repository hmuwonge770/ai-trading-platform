"""Strategy specifications and deterministic strategy execution."""

from packages.strategies.config import MovingAverageCrossoverConfig, StrategyConfig
from packages.strategies.fingerprint import strategy_fingerprint
from packages.strategies.models import MarketBar, Signal, StrategySignal
from packages.strategies.moving_average import MovingAverageCrossoverStrategy
from packages.strategies.registry import build_strategy

__all__ = [
    "MarketBar",
    "MovingAverageCrossoverConfig",
    "MovingAverageCrossoverStrategy",
    "Signal",
    "StrategyConfig",
    "StrategySignal",
    "build_strategy",
    "strategy_fingerprint",
]
