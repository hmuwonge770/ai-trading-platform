"""Deterministic governance boundary for autonomous risk policy."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import math


class RiskPolicyReason(str):
    APPROVED = "approved"
    NO_CAPACITY = "no_risk_capacity"
    POLICY_LIMIT = "risk_policy_limit"
    IDENTITY_REQUIRED = "strategy_identity_required"
    INVALID_INPUT = "invalid_risk_input"


def _decimal(value: Decimal | int | float | str, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{field} must be a finite decimal") from None
    if not result.is_finite() or (isinstance(value, float) and not math.isfinite(value)):
        raise ValueError(f"{field} must be a finite decimal")
    if result < 0:
        raise ValueError(f"{field} cannot be negative")
    return result


@dataclass(frozen=True, slots=True)
class RiskPolicy:
    """Externally approved immutable risk ceilings."""

    max_total_exposure: Decimal
    max_strategy_exposure: Decimal
    max_single_order_notional: Decimal

    def __post_init__(self) -> None:
        total = _decimal(self.max_total_exposure, "max_total_exposure")
        strategy = _decimal(self.max_strategy_exposure, "max_strategy_exposure")
        order = _decimal(self.max_single_order_notional, "max_single_order_notional")
        if strategy > total:
            raise ValueError("max_strategy_exposure cannot exceed max_total_exposure")
        if order > total:
            raise ValueError("max_single_order_notional cannot exceed max_total_exposure")
        object.__setattr__(self, "max_total_exposure", total)
        object.__setattr__(self, "max_strategy_exposure", strategy)
        object.__setattr__(self, "max_single_order_notional", order)


@dataclass(frozen=True, slots=True)
class RiskPolicyRequest:
    strategy_version_id: str
    existing_total_exposure: Decimal
    existing_strategy_exposure: Decimal
    requested_notional: Decimal


@dataclass(frozen=True, slots=True)
class RiskPolicyReport:
    strategy_version_id: str
    approved: bool
    approved_notional: Decimal
    total_capacity: Decimal
    strategy_capacity: Decimal
    order_capacity: Decimal
    reason: str


class AutonomousRiskPolicyGovernance:
    """Evaluate proposed exposure without changing policy or executing trades."""

    def evaluate(self, policy: RiskPolicy, request: RiskPolicyRequest) -> RiskPolicyReport:
        strategy_id = request.strategy_version_id.strip()
        if not strategy_id:
            raise ValueError(RiskPolicyReason.IDENTITY_REQUIRED)

        total_exposure = _decimal(request.existing_total_exposure, "existing_total_exposure")
        strategy_exposure = _decimal(request.existing_strategy_exposure, "existing_strategy_exposure")
        requested = _decimal(request.requested_notional, "requested_notional")

        if strategy_exposure > total_exposure:
            raise ValueError("strategy exposure cannot exceed total exposure")

        total_capacity = max(Decimal("0"), policy.max_total_exposure - total_exposure)
        strategy_capacity = max(Decimal("0"), policy.max_strategy_exposure - strategy_exposure)
        order_capacity = policy.max_single_order_notional
        approved = min(requested, total_capacity, strategy_capacity, order_capacity)

        if approved == 0:
            reason = RiskPolicyReason.NO_CAPACITY if requested > 0 else RiskPolicyReason.POLICY_LIMIT
            return RiskPolicyReport(strategy_id, False, approved, total_capacity, strategy_capacity, order_capacity, reason)
        if approved < requested:
            return RiskPolicyReport(strategy_id, False, approved, total_capacity, strategy_capacity, order_capacity, RiskPolicyReason.POLICY_LIMIT)
        return RiskPolicyReport(strategy_id, True, approved, total_capacity, strategy_capacity, order_capacity, RiskPolicyReason.APPROVED)
