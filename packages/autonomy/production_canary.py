"""Bounded governance for production-canary rollout planning.

This module is a control-plane decision layer. It never starts a canary,
changes runtime configuration, widens risk/capital limits, or submits orders.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum
import hashlib
import math
from uuid import UUID


class ProductionCanaryAction(StrEnum):
    START = "start"
    HOLD = "hold"
    ABORT = "abort"


@dataclass(frozen=True, slots=True)
class ProductionCanaryPolicy:
    """Externally approved, immutable canary boundaries."""

    max_cohort_percent: Decimal = Decimal("1")
    minimum_evidence_samples: int = 100
    max_error_rate_percent: Decimal = Decimal("1")
    max_reconciliation_failures: int = 0
    max_drawdown_percent: Decimal = Decimal("2")
    max_slippage_percent: Decimal = Decimal("1")

    def __post_init__(self) -> None:
        for name in (
            "max_cohort_percent",
            "max_error_rate_percent",
            "max_drawdown_percent",
            "max_slippage_percent",
        ):
            value = _decimal(getattr(self, name), name)
            if value < 0:
                raise ValueError(f"{name} cannot be negative")
            if name == "max_cohort_percent" and value > 100:
                raise ValueError("max_cohort_percent cannot exceed 100")
            object.__setattr__(self, name, value)
        if self.minimum_evidence_samples < 0:
            raise ValueError("minimum_evidence_samples cannot be negative")
        if self.max_reconciliation_failures < 0:
            raise ValueError("max_reconciliation_failures cannot be negative")


@dataclass(frozen=True, slots=True)
class ProductionCanaryRequest:
    strategy_version_id: UUID
    requested_cohort_percent: Decimal
    evidence_samples: int
    observed_error_rate_percent: Decimal
    reconciliation_failures: int
    observed_drawdown_percent: Decimal
    observed_slippage_percent: Decimal
    promotion_approved: bool
    risk_approved: bool
    capital_approved: bool
    runtime_ready: bool
    kill_switch_clear: bool
    explicit_operator_approval: bool


@dataclass(frozen=True, slots=True)
class ProductionCanaryReport:
    strategy_version_id: UUID
    action: ProductionCanaryAction
    safe: bool
    cohort_percent: Decimal
    assigned_to_cohort: bool
    reasons: tuple[str, ...] = ()

    @property
    def should_start(self) -> bool:
        return self.action is ProductionCanaryAction.START


def _decimal(value: Decimal | int | float | str, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{field} must be a finite decimal") from None
    if not result.is_finite() or (isinstance(value, float) and not math.isfinite(value)):
        raise ValueError(f"{field} must be a finite decimal")
    return result


def _cohort_percent(strategy_version_id: UUID) -> Decimal:
    digest = hashlib.sha256(strategy_version_id.bytes).digest()
    bucket = int.from_bytes(digest[:8], "big") % 10000
    return Decimal(bucket) / Decimal(100)


class AutonomousProductionCanaryGovernance:
    """Deterministically plan a bounded production-canary cohort."""

    def __init__(self, *, policy: ProductionCanaryPolicy | None = None) -> None:
        self.policy = policy or ProductionCanaryPolicy()

    def evaluate(self, request: ProductionCanaryRequest) -> ProductionCanaryReport:
        requested = _decimal(request.requested_cohort_percent, "requested_cohort_percent")
        error_rate = _decimal(request.observed_error_rate_percent, "observed_error_rate_percent")
        drawdown = _decimal(request.observed_drawdown_percent, "observed_drawdown_percent")
        slippage = _decimal(request.observed_slippage_percent, "observed_slippage_percent")
        if any(value < 0 for value in (requested, error_rate, drawdown, slippage)):
            raise ValueError("canary percentages cannot be negative")
        if requested > self.policy.max_cohort_percent:
            raise ValueError("requested_cohort_percent exceeds approved canary boundary")
        if request.evidence_samples < 0 or request.reconciliation_failures < 0:
            raise ValueError("canary counts cannot be negative")

        reasons: list[str] = []
        if not request.explicit_operator_approval:
            reasons.append("operator_approval_required")
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
        if request.evidence_samples < self.policy.minimum_evidence_samples:
            reasons.append("insufficient_evidence")
        if error_rate > self.policy.max_error_rate_percent:
            reasons.append("error_rate_exceeded")
        if request.reconciliation_failures > self.policy.max_reconciliation_failures:
            reasons.append("reconciliation_failures_exceeded")
        if drawdown > self.policy.max_drawdown_percent:
            reasons.append("drawdown_exceeded")
        if slippage > self.policy.max_slippage_percent:
            reasons.append("slippage_exceeded")

        if any(reason in reasons for reason in (
            "promotion_governance_not_approved",
            "risk_governance_not_approved",
            "capital_governance_not_approved",
            "runtime_not_ready",
            "deployment_kill_switch_active",
            "error_rate_exceeded",
            "reconciliation_failures_exceeded",
            "drawdown_exceeded",
            "slippage_exceeded",
        )):
            action = ProductionCanaryAction.ABORT
        elif reasons:
            action = ProductionCanaryAction.HOLD
        else:
            action = ProductionCanaryAction.START

        assigned = _cohort_percent(request.strategy_version_id) < requested
        if action is ProductionCanaryAction.START and not assigned:
            action = ProductionCanaryAction.HOLD
            reasons.append("strategy_not_assigned_to_canary_cohort")

        return ProductionCanaryReport(
            strategy_version_id=request.strategy_version_id,
            action=action,
            safe=action is not ProductionCanaryAction.ABORT,
            cohort_percent=requested,
            assigned_to_cohort=assigned,
            reasons=tuple(dict.fromkeys(reasons)),
        )
