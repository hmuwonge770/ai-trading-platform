"""Bounded governance for controlled production expansion.

AX plans an expansion within an externally approved ceiling. It never widens
capital or risk limits, activates live execution, submits orders, or changes
runtime/authorization state.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from uuid import UUID


class ExpansionAction(StrEnum):
    EXPAND = "expand"
    HOLD = "hold"
    ABORT = "abort"


@dataclass(frozen=True, slots=True)
class ControlledExpansionPolicy:
    """Immutable externally approved expansion boundary."""

    maximum_cohort_percent: Decimal = Decimal("5")
    maximum_step_percent: Decimal = Decimal("1")
    minimum_soak_samples: int = 1000
    maximum_error_rate_percent: Decimal = Decimal("1")
    maximum_drawdown_percent: Decimal = Decimal("2")
    maximum_slippage_percent: Decimal = Decimal("1")
    maximum_reconciliation_failures: int = 0

    def __post_init__(self) -> None:
        for name in (
            "maximum_cohort_percent",
            "maximum_step_percent",
            "maximum_error_rate_percent",
            "maximum_drawdown_percent",
            "maximum_slippage_percent",
        ):
            value = _decimal(getattr(self, name), name)
            if value < 0:
                raise ValueError(f"{name} cannot be negative")
            object.__setattr__(self, name, value)
        if self.maximum_cohort_percent > 100 or self.maximum_step_percent > 100:
            raise ValueError("expansion percentages cannot exceed 100")
        if self.maximum_step_percent > self.maximum_cohort_percent:
            raise ValueError("maximum_step_percent cannot exceed maximum_cohort_percent")
        if self.minimum_soak_samples < 0 or self.maximum_reconciliation_failures < 0:
            raise ValueError("expansion counts cannot be negative")


@dataclass(frozen=True, slots=True)
class ExpansionRequest:
    strategy_version_id: UUID
    current_cohort_percent: Decimal
    requested_cohort_percent: Decimal
    soak_samples: int
    observed_error_rate_percent: Decimal
    observed_drawdown_percent: Decimal
    observed_slippage_percent: Decimal
    reconciliation_failures: int
    canary_completed: bool
    soak_completed: bool
    promotion_approved: bool
    risk_approved: bool
    capital_approved: bool
    runtime_ready: bool
    kill_switch_clear: bool
    explicit_operator_approval: bool


@dataclass(frozen=True, slots=True)
class ExpansionReport:
    strategy_version_id: UUID
    action: ExpansionAction
    safe: bool
    current_cohort_percent: Decimal
    requested_cohort_percent: Decimal
    approved_delta_percent: Decimal
    reasons: tuple[str, ...] = ()

    @property
    def should_expand(self) -> bool:
        return self.action is ExpansionAction.EXPAND


def _decimal(value: Decimal | int | float | str, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{field} must be a finite decimal") from None
    if not result.is_finite():
        raise ValueError(f"{field} must be a finite decimal")
    return result
