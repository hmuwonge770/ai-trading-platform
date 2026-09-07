"""Autonomous risk-gated execution orchestration.

This stage deliberately delegates transport to an injected execution service.
It cannot create an order from an unapproved decision and has no exchange
credentials or exchange client of its own.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from collections.abc import Callable

from packages.autonomy.risk import AutonomousRiskResult
from packages.execution.service import ExecutionResult
from packages.strategies.models import MarketBar


class ExecutionSubmitter:
    def submit(self, order, risk_decision, candle: MarketBar) -> ExecutionResult:
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class AutonomousExecutionOutcome:
    submitted: bool
    reason: str
    result: ExecutionResult | None


class AutonomousExecutionLoop:
    """Submit only risk-approved intents, once per client order id."""

    def __init__(
        self,
        submitter: ExecutionSubmitter,
        *,
        dedupe_capacity: int = 10_000,
    ) -> None:
        if dedupe_capacity <= 0:
            raise ValueError("dedupe_capacity must be positive")
        self._submitter = submitter
        self._seen: set[str] = set()
        self._seen_order: deque[str] = deque(maxlen=dedupe_capacity)

    def process(
        self,
        risk_result: AutonomousRiskResult,
        candle: MarketBar,
    ) -> AutonomousExecutionOutcome:
        if not risk_result.approved:
            return AutonomousExecutionOutcome(False, "risk approval is required", None)
        if risk_result.order is None or risk_result.gateway_decision is None:
            return AutonomousExecutionOutcome(False, "approved risk result is incomplete", None)

        order_id = risk_result.order.client_order_id
        if order_id in self._seen:
            return AutonomousExecutionOutcome(False, "duplicate autonomous order suppressed", None)
        if candle.symbol != risk_result.order.symbol:
            return AutonomousExecutionOutcome(False, "candle symbol does not match order", None)
        if candle.timeframe != risk_result.order.timeframe:
            return AutonomousExecutionOutcome(False, "candle timeframe does not match order", None)

        result = self._submitter.submit(
            risk_result.order,
            risk_result.gateway_decision,
            candle,
        )
        self._remember(order_id)
        return AutonomousExecutionOutcome(True, result.reason, result)

    def _remember(self, order_id: str) -> None:
        if len(self._seen_order) == self._seen_order.maxlen:
            self._seen.discard(self._seen_order[0])
        self._seen_order.append(order_id)
        self._seen.add(order_id)
