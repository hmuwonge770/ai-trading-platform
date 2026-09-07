"""Deterministic market decision engine for autonomous trading.

The engine converts a normalized market snapshot into a bounded decision.
AI/model output can be supplied as evidence, but it cannot bypass these
structural checks or directly submit orders.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from decimal import Decimal


class DecisionAction(StrEnum):
    HOLD = "HOLD"
    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True, slots=True)
class MarketSnapshot:
    symbol: str
    price: Decimal
    ema_fast: Decimal
    ema_slow: Decimal
    rsi: Decimal
    timestamp: int

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol is required")
        if self.price <= 0:
            raise ValueError("price must be positive")
        if not 0 <= self.rsi <= 100:
            raise ValueError("rsi must be between 0 and 100")
        if self.timestamp <= 0:
            raise ValueError("timestamp must be positive")


@dataclass(frozen=True, slots=True)
class Decision:
    action: DecisionAction
    symbol: str
    confidence: Decimal
    reason: str
    timestamp: int


@dataclass(frozen=True, slots=True)
class DecisionPolicy:
    min_confidence: Decimal = Decimal("0.70")
    oversold_rsi: Decimal = Decimal("30")
    overbought_rsi: Decimal = Decimal("70")

    def __post_init__(self) -> None:
        if not Decimal("0") < self.min_confidence <= Decimal("1"):
            raise ValueError("min_confidence must be in (0, 1]")
        if not 0 <= self.oversold_rsi < self.overbought_rsi <= 100:
            raise ValueError("invalid RSI thresholds")


class AutonomousDecisionEngine:
    """Produce bounded decisions without exchange or credential access."""

    def __init__(self, policy: DecisionPolicy | None = None) -> None:
        self.policy = policy or DecisionPolicy()

    def evaluate(self, snapshot: MarketSnapshot) -> Decision:
        if snapshot.ema_fast > snapshot.ema_slow and snapshot.rsi < self.policy.overbought_rsi:
            confidence = Decimal("0.80")
            action = DecisionAction.BUY
            reason = "fast EMA above slow EMA with non-overbought RSI"
        elif snapshot.ema_fast < snapshot.ema_slow and snapshot.rsi > self.policy.oversold_rsi:
            confidence = Decimal("0.80")
            action = DecisionAction.SELL
            reason = "fast EMA below slow EMA with non-oversold RSI"
        else:
            confidence = Decimal("0")
            action = DecisionAction.HOLD
            reason = "market conditions do not satisfy the decision policy"

        if confidence < self.policy.min_confidence:
            action = DecisionAction.HOLD
            reason = "decision confidence is below the configured threshold"

        return Decision(action, snapshot.symbol, confidence, reason, snapshot.timestamp)
