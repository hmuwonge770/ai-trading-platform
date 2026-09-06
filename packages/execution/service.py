from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from packages.execution.simulator import SimulatedFill, SimulatedOrder
from packages.risk import RiskDecision, RiskReason
from packages.strategies.models import MarketBar
from packages.trading.paper import OrderIntent


class ExecutionBackend(Protocol):
    def execute(self, order: OrderIntent, candle: MarketBar) -> tuple[SimulatedOrder, SimulatedFill | None]: ...


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    accepted: bool
    reason: str
    simulated_order: SimulatedOrder | None
    fill: SimulatedFill | None


class ExecutionService:
    """Execution boundary that requires an independent risk approval.

    The service owns order-submission orchestration, but the backend is
    injected. Stage 16 therefore cannot accidentally acquire exchange access;
    Stage 17 can supply a testnet backend behind this same boundary.
    """

    def __init__(self, backend: ExecutionBackend) -> None:
        self.backend = backend
        self._results: dict[str, ExecutionResult] = {}

    def submit(
        self,
        order: OrderIntent,
        risk_decision: RiskDecision,
        candle: MarketBar,
    ) -> ExecutionResult:
        """Submit exactly once after a positive risk decision."""
        existing = self._results.get(order.client_order_id)
        if existing is not None:
            return existing

        if not risk_decision.approved or risk_decision.reason != RiskReason.APPROVED:
            result = ExecutionResult(
                accepted=False,
                reason="order was not approved by the deterministic risk gateway",
                simulated_order=None,
                fill=None,
            )
            self._results[order.client_order_id] = result
            return result
        if risk_decision.order_id != order.client_order_id:
            result = ExecutionResult(
                accepted=False,
                reason="risk decision does not match the order",
                simulated_order=None,
                fill=None,
            )
            self._results[order.client_order_id] = result
            return result

        simulated_order, fill = self.backend.execute(order, candle)
        result = ExecutionResult(
            accepted=simulated_order.status.value != "rejected",
            reason=simulated_order.reason,
            simulated_order=simulated_order,
            fill=fill,
        )
        self._results[order.client_order_id] = result
        return result
