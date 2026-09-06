from __future__ import annotations

from collections.abc import Callable
from typing import Any

from packages.strategies.config import MovingAverageCrossoverConfig
from packages.strategies.moving_average import MovingAverageCrossoverStrategy
from packages.strategies.base import Strategy


StrategyFactory = Callable[[Any], Strategy]


STRATEGY_FACTORIES: dict[str, StrategyFactory] = {
    "moving_average_crossover": MovingAverageCrossoverStrategy,
}


def build_strategy(family: str, config: Any) -> Strategy:
    """Build a registered deterministic strategy from validated configuration."""
    if family == "moving_average_crossover" and not isinstance(config, MovingAverageCrossoverConfig):
        config = MovingAverageCrossoverConfig.model_validate(config)

    try:
        factory = STRATEGY_FACTORIES[family]
    except KeyError as exc:
        raise ValueError(f"unsupported strategy family: {family}") from exc

    return factory(config)
