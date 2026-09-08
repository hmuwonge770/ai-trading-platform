"""Governance adapter enforcing an externally supplied risk ceiling."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .capital_allocation import (
    AutonomousCapitalAllocator,
    CapitalAllocationReport,
    CapitalAllocationRequest,
)


@dataclass(frozen=True, slots=True)
class CapitalGovernanceContext:
    portfolio_ceiling: Decimal
    strategy_ceiling: Decimal
    risk_ceiling: Decimal


class AutonomousCapitalAllocationGovernance:
    """Compose allocation with an immutable, externally approved risk ceiling."""

    def __init__(self, allocator: AutonomousCapitalAllocator | None = None) -> None:
        self._allocator = allocator or AutonomousCapitalAllocator()

    def evaluate(
        self,
        *,
        strategy_version_id: str,
        context: CapitalGovernanceContext,
        existing_exposure: Decimal,
        requested_capital: Decimal,
    ) -> CapitalAllocationReport:
        effective_strategy_ceiling = min(context.strategy_ceiling, context.risk_ceiling)
        return self._allocator.evaluate(
            CapitalAllocationRequest(
                strategy_version_id=strategy_version_id,
                portfolio_ceiling=context.portfolio_ceiling,
                strategy_ceiling=effective_strategy_ceiling,
                existing_exposure=existing_exposure,
                requested_capital=requested_capital,
            )
        )
