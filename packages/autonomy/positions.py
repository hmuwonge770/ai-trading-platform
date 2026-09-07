"""Deterministic position-maintenance decisions for autonomous trading.

The agent manages existing spot exposure only. It never opens a position and
never submits an order. Its output remains subject to the autonomous risk and
execution boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class PositionAction(StrEnum):
    HOLD = "HOLD"
    EXIT = "EXIT"


@dataclass(frozen=True, slots=True)
class ManagedPosition:
    symbol: str
    quantity: Decimal
    average_entry_price: Decimal
    current_price: Decimal
    opened_at: int

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol is required")
        if self.quantity <= 0:
            raise ValueError("position quantity must be positive")
        if self.average_entry_price <= 0 or self.current_price <= 0:
            raise ValueError("position prices must be positive")
        if self.opened_at <= 0:
            raise ValueError("opened_at must be positive")


@dataclass(frozen=True, slots=True)
class PositionPolicy:
    stop_loss_fraction: Decimal = Decimal("0.02")
    take_profit_fraction: Decimal = Decimal("0.04")
    max_quote_age_seconds: int = 30

    def __post_init__(self) -> None:
        if not 0 < self.stop_loss_fraction < 1:
            raise ValueError("stop_loss_fraction must be in (0, 1)")
        if not self.take_profit_fraction > 0:
            raise ValueError("take_profit_fraction must be positive")
        if self.max_quote_age_seconds <= 0:
            raise ValueError("max_quote_age_seconds must be positive")


@dataclass(frozen=True, slots=True)
class PositionDecision:
    action: PositionAction
    symbol: str
    reason: str
    timestamp: int


class AutonomousPositionAgent:
    """Maintain existing positions with deterministic exit policy."""

    def __init__(self, policy: PositionPolicy | None = None) -> None:
        self.policy = policy or PositionPolicy()

    def evaluate(
        self,
        position: ManagedPosition,
        *,
        quote_timestamp: int,
        now: int,
    ) -> PositionDecision:
        if quote_timestamp > now:
            raise ValueError("position quote cannot be from the future")
        if now - quote_timestamp > self.policy.max_quote_age_seconds:
            return PositionDecision(
                PositionAction.HOLD,
                position.symbol,
                "position quote is stale; do not create an exit from stale data",
                now,
            )

        stop_price = position.average_entry_price * (Decimal("1") - self.policy.stop_loss_fraction)
        target_price = position.average_entry_price * (Decimal("1") + self.policy.take_profit_fraction)

        if position.current_price <= stop_price:
            return PositionDecision(
                PositionAction.EXIT,
                position.symbol,
                "stop-loss threshold reached",
                now,
            )
        if position.current_price >= target_price:
            return PositionDecision(
                PositionAction.EXIT,
                position.symbol,
                "take-profit threshold reached",
                now,
            )
        return PositionDecision(
            PositionAction.HOLD,
            position.symbol,
            "position remains within configured maintenance bounds",
            now,
        )
