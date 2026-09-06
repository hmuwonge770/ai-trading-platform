"""Core trading-domain primitives."""

from packages.trading.paper import (
    OrderIntent,
    PaperCandleResult,
    PaperFill,
    PaperTradingConfig,
    PaperTradingEngine,
    TradingSignal,
)

__all__ = [
    "OrderIntent",
    "PaperCandleResult",
    "PaperFill",
    "PaperTradingConfig",
    "PaperTradingEngine",
    "TradingSignal",
]
