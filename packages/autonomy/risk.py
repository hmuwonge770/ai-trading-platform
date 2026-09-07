"""Autonomous risk boundary between AI decisions and order execution.

This module does not execute orders. It converts an approved autonomous
Decision into an OrderIntent candidate and subjects it to freshness, order-rate,
liquidity, and the existing deterministic RiskGateway checks.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from decimal import Decimal
from time import time
from uuid import uuid4

from packages.autonomy.decision import Decision, DecisionAction
from packages.portfolio import PortfolioSnapshot
from packages.risk.gateway import RiskContext, RiskDecision, RiskGateway
from packages.strategies.models import Signal
from packages.trading.paper import OrderIntent


class AutonomousRiskReason(str):
    HOLD = "hold"
    STALE_DECISION = "stale_decision"
    INVALID_QUANTITY = "invalid_quantity"
    ORDER_RATE_LIMIT = "order_rate_limit"
    LIQUIDITY_LIMIT = "liquidity_limit"
    GATEWAY_REJECTED = "gateway_rejected"


@dataclass(frozen=True, slots=True)
class AutonomousRiskPolicy:
    max_decision_age_seconds: int = 60
    max_orders_per_window: int = 10
    order_window_seconds: int = 60
    max_liquidity_fraction: Decimal = Decimal("0.10")

    def __post_init__(self) -> None:
        if self.max_decision_age_seconds <= 0:
            raise ValueError("max_decision_age_seconds must be positive")
        if self.max_orders_per_window <= 0:
            raise ValueError("max_orders_per_window must be positive")
        if self.order_window_seconds <= 0:
            raise ValueError("order_window_seconds must be positive")
        if not 0 < self.max_liquidity_fraction <= 1:
            raise ValueError("max_liquidity_fraction must be in (0, 1]")


@dataclass(frozen=True, slots=True)
class AutonomousRiskResult:
    approved: bool
    reason: str
    message: str
    decision: Decision
    order: OrderIntent | None
    gateway_decision: RiskDecision | None


class AutonomousRiskEngine:
    """Apply deterministic autonomous risk policy before execution."""

    def __init__(
        self,
        gateway: RiskGateway,
        *,
        policy: AutonomousRiskPolicy | None = None,
        clock=time,
    ) -> None:
        self._gateway = gateway
        self.policy = policy or AutonomousRiskPolicy()
        self._clock = clock
        self._orders: deque[float] = deque()

    def evaluate(
        self,
        decision: Decision,
        *,
        quantity: Decimal,
        timeframe: str,
        strategy_version_id: str,
        portfolio: PortfolioSnapshot,
        current_price: Decimal,
        total_exposure: Decimal,
        daily_realized_pnl: Decimal,
        liquidity_quote_volume: Decimal,
        now: int | None = None,
    ) -> AutonomousRiskResult:
        current_time = int(self._clock()) if now is None else now

        if decision.action is DecisionAction.HOLD:
            return self._reject(decision, AutonomousRiskReason.HOLD, "HOLD never becomes an order")
        if current_time < decision.timestamp:
            return self._reject(
                decision,
                AutonomousRiskReason.STALE_DECISION,
                "decision timestamp is in the future",
            )
        if current_time - decision.timestamp > self.policy.max_decision_age_seconds:
            return self._reject(
                decision,
                AutonomousRiskReason.STALE_DECISION,
                "autonomous decision is stale",
            )
        if quantity <= 0:
            return self._reject(
                decision,
                AutonomousRiskReason.INVALID_QUANTITY,
                "order quantity must be positive",
            )

        self._prune(current_time)
        if len(self._orders) >= self.policy.max_orders_per_window:
            return self._reject(
                decision,
                AutonomousRiskReason.ORDER_RATE_LIMIT,
                "autonomous order-rate limit has been reached",
            )

        order_notional = quantity * current_price
        if liquidity_quote_volume <= 0 or order_notional > liquidity_quote_volume * self.policy.max_liquidity_fraction:
            return self._reject(
                decision,
                AutonomousRiskReason.LIQUIDITY_LIMIT,
                "order exceeds the configured fraction of observed quote liquidity",
            )

        signal_id = uuid4()
        order = OrderIntent(
            intent_id=uuid4(),
            signal_id=signal_id,
            strategy_version_id=strategy_version_id,
            symbol=decision.symbol,
            timeframe=timeframe,
            side=Signal.BUY if decision.action is DecisionAction.BUY else Signal.SELL,
            quantity=quantity,
            reference_price=current_price,
            client_order_id=f"auto-{signal_id}",
            reason=decision.reason,
        )
        gateway_decision = self._gateway.evaluate(
            order,
            RiskContext(
                portfolio=portfolio,
                current_price=current_price,
                total_exposure=total_exposure,
                daily_realized_pnl=daily_realized_pnl,
            ),
        )
        if not gateway_decision.approved:
            return AutonomousRiskResult(
                False,
                AutonomousRiskReason.GATEWAY_REJECTED,
                gateway_decision.message,
                decision,
                order,
                gateway_decision,
            )

        self._orders.append(float(current_time))
        return AutonomousRiskResult(
            True,
            "approved",
            "decision passed autonomous and deterministic risk checks",
            decision,
            order,
            gateway_decision,
        )

    def _prune(self, now: int) -> None:
        cutoff = now - self.policy.order_window_seconds
        while self._orders and self._orders[0] <= cutoff:
            self._orders.popleft()

    @staticmethod
    def _reject(decision: Decision, reason: str, message: str) -> AutonomousRiskResult:
        return AutonomousRiskResult(False, reason, message, decision, None, None)
