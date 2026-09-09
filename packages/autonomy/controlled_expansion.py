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
            "maximum_cohort_percent", "maximum_step_percent", "maximum_error_rate_percent",
            "maximum_drawdown_percent", "maximum_slippage_percent",
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


def evaluate_expansion(request: ExpansionRequest, *, policy: ControlledExpansionPolicy | None = None) -> ExpansionReport:
    policy = policy or ControlledExpansionPolicy()
    current = _decimal(request.current_cohort_percent, "current_cohort_percent")
    requested = _decimal(request.requested_cohort_percent, "requested_cohort_percent")
    error = _decimal(request.observed_error_rate_percent, "observed_error_rate_percent")
    drawdown = _decimal(request.observed_drawdown_percent, "observed_drawdown_percent")
    slippage = _decimal(request.observed_slippage_percent, "observed_slippage_percent")
    if any(value < 0 for value in (current, requested, error, drawdown, slippage)):
        raise ValueError("expansion percentages cannot be negative")
    if current > policy.maximum_cohort_percent:
        raise ValueError("current cohort exceeds approved expansion boundary")
    if requested < current:
        raise ValueError("requested cohort cannot reduce the current cohort")
    delta = requested - current
    if requested > policy.maximum_cohort_percent or delta > policy.maximum_step_percent:
        raise ValueError("requested expansion exceeds approved boundary")
    if request.soak_samples < 0 or request.reconciliation_failures < 0:
        raise ValueError("expansion counts cannot be negative")

    reasons: list[str] = []
    if not request.canary_completed:
        reasons.append("canary_not_completed")
    if not request.soak_completed:
        reasons.append("soak_not_completed")
    if not request.promotion_approved:
        reasons.append("promotion_governance_not_approved")
    if not request.risk_approved:
        reasons.append("risk_governance_not_approved")
    if not request.capital_approved:
        reasons.append("capital_governance_not_approved")
    if not request.runtime_ready:
        reasons.append("runtime_not_ready")
    if not request.kill_switch_clear:
        reasons.append("deployment_kill_switch_active")
    if not request.explicit_operator_approval:
        reasons.append("operator_approval_required")
    if request.soak_samples < policy.minimum_soak_samples:
        reasons.append("insufficient_soak_evidence")
    if error > policy.maximum_error_rate_percent:
        reasons.append("error_rate_exceeded")
    if drawdown > policy.maximum_drawdown_percent:
        reasons.append("drawdown_exceeded")
    if slippage > policy.maximum_slippage_percent:
        reasons.append("slippage_exceeded")
    if request.reconciliation_failures > policy.maximum_reconciliation_failures:
        reasons.append("reconciliation_failures_exceeded")

    hard_failures = {
        "canary_not_completed", "soak_not_completed", "promotion_governance_not_approved",
        "risk_governance_not_approved", "capital_governance_not_approved", "runtime_not_ready",
        "deployment_kill_switch_active", "error_rate_exceeded", "drawdown_exceeded",
        "slippage_exceeded", "reconciliation_failures_exceeded",
    }
    if any(reason in hard_failures for reason in reasons):
        action = ExpansionAction.ABORT
    elif reasons:
        action = ExpansionAction.HOLD
    elif delta == 0:
        action = ExpansionAction.HOLD
        reasons.append("no_expansion_requested")
    else:
        action = ExpansionAction.EXPAND

    return ExpansionReport(
        request.strategy_version_id, action, action is not ExpansionAction.ABORT,
        current, requested, delta, tuple(dict.fromkeys(reasons)),
    )
