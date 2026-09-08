"""Deterministic, bounded autonomous capital allocation planning."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import math


@dataclass(frozen=True, slots=True)
class CapitalAllocationRequest:
    strategy_version_id: str
    portfolio_ceiling: Decimal
    strategy_ceiling: Decimal
    existing_exposure: Decimal
    requested_capital: Decimal


@dataclass(frozen=True, slots=True)
class CapitalAllocationReport:
    strategy_version_id: str
    approved_allocation: Decimal
    portfolio_capacity: Decimal
    strategy_capacity: Decimal
    safe: bool
    reasons: tuple[str, ...] = ()

    @property
    def can_allocate(self) -> bool:
        return self.safe and self.approved_allocation > Decimal("0")


def _decimal(value: Decimal | int | float | str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError("monetary values must be finite decimals") from None
    if not result.is_finite() or (isinstance(value, float) and not math.isfinite(value)):
        raise ValueError("monetary values must be finite decimals")
    return result


class AutonomousCapitalAllocator:
    """Plan allocation only; never mutates ceilings or executes orders."""

    def evaluate(self, request: CapitalAllocationRequest) -> CapitalAllocationReport:
        strategy_id = request.strategy_version_id.strip()
        if not strategy_id:
            raise ValueError("strategy_version_id is required")

        ceiling = _decimal(request.portfolio_ceiling)
        strategy_ceiling = _decimal(request.strategy_ceiling)
        exposure = _decimal(request.existing_exposure)
        requested = _decimal(request.requested_capital)

        if min(ceiling, strategy_ceiling, exposure, requested) < Decimal("0"):
            raise ValueError("monetary values cannot be negative")

        portfolio_capacity = max(Decimal("0"), ceiling - exposure)
        strategy_capacity = max(Decimal("0"), strategy_ceiling - exposure)
        approved = min(requested, portfolio_capacity, strategy_capacity)

        reasons: list[str] = []
        if portfolio_capacity == Decimal("0"):
            reasons.append("portfolio_ceiling_exhausted")
        if strategy_capacity == Decimal("0"):
            reasons.append("strategy_ceiling_exhausted")
        if approved < requested:
            reasons.append("allocation_bounded_by_ceiling")
        if approved == Decimal("0") and not reasons:
            reasons.append("no_allocation_requested")

        return CapitalAllocationReport(
            strategy_version_id=strategy_id,
            approved_allocation=approved,
            portfolio_capacity=portfolio_capacity,
            strategy_capacity=strategy_capacity,
            safe=True,
            reasons=tuple(reasons),
        )
