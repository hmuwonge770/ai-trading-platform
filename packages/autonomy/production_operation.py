"""Final-stage bounded autonomous production-operation contract."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from math import isfinite


class ProductionOperationAction(StrEnum):
    OPERATE = "operate"
    HOLD = "hold"
    HALT = "halt"


@dataclass(frozen=True, slots=True)
class ProductionOperationPolicy:
    """Immutable ceilings and hard safety requirements for AZ."""

    maximum_cohort_percent: Decimal = Decimal("5")
    maximum_daily_loss_percent: Decimal = Decimal("2")
    maximum_drawdown_percent: Decimal = Decimal("2")
    maximum_error_rate_percent: Decimal = Decimal("1")
    maximum_slippage_percent: Decimal = Decimal("1")
    maximum_reconciliation_failures: int = 0
    require_live_authorization: bool = True
    require_runtime_enabled: bool = True
    require_operator_shutdown: bool = True
    require_strategy_identity: bool = True
    require_capital_governance: bool = True
    require_risk_governance: bool = True

    def __post_init__(self) -> None:
        for name in (
            "maximum_cohort_percent",
            "maximum_daily_loss_percent",
            "maximum_drawdown_percent",
            "maximum_error_rate_percent",
            "maximum_slippage_percent",
        ):
            value = getattr(self, name)
            if not value.is_finite() or value < 0:
                raise ValueError(f"{name} must be finite and non-negative")
        if self.maximum_cohort_percent > Decimal("5"):
            raise ValueError("maximum_cohort_percent exceeds AZ hard ceiling")
        if self.maximum_daily_loss_percent > Decimal("2"):
            raise ValueError("maximum_daily_loss_percent exceeds AZ hard ceiling")
        if self.maximum_drawdown_percent > Decimal("2"):
            raise ValueError("maximum_drawdown_percent exceeds AZ hard ceiling")
        if self.maximum_error_rate_percent > Decimal("1"):
            raise ValueError("maximum_error_rate_percent exceeds AZ hard ceiling")
        if self.maximum_slippage_percent > Decimal("1"):
            raise ValueError("maximum_slippage_percent exceeds AZ hard ceiling")
        if self.maximum_reconciliation_failures < 0:
            raise ValueError("maximum_reconciliation_failures must be non-negative")


@dataclass(frozen=True, slots=True)
class ProductionOperationObservation:
    strategy_version_id: str | None
    strategy_fingerprint: str | None
    live_authorized: bool
    runtime_enabled: bool
    operator_shutdown_available: bool
    deployment_kill_switch_active: bool
    capital_approved: bool
    risk_approved: bool
    readiness_approved: bool
    lifecycle_validation_passed: bool
    canary_completed: bool
    soak_completed: bool
    failure_testing_passed: bool
    security_secure: bool
    incident_recovery_verified: bool
    reconciliation_failures: int
    daily_loss_percent: Decimal
    drawdown_percent: Decimal
    error_rate_percent: Decimal
    slippage_percent: Decimal


@dataclass(frozen=True, slots=True)
class ProductionOperationAssessment:
    action: ProductionOperationAction
    reasons: tuple[str, ...]
    strategy_version_id: str | None
    strategy_fingerprint: str | None


def _valid_decimal(value: Decimal) -> bool:
    return value.is_finite() and value >= 0


def assess_production_operation(
    observation: ProductionOperationObservation,
    policy: ProductionOperationPolicy | None = None,
) -> ProductionOperationAssessment:
    """Deterministically evaluate whether bounded production operation may continue."""
    policy = policy or ProductionOperationPolicy()
    reasons: list[str] = []

    if policy.require_strategy_identity and (
        not observation.strategy_version_id or not observation.strategy_fingerprint
    ):
        reasons.append("strategy_identity_missing")
    if not observation.live_authorized:
        reasons.append("live_authorization_missing")
    if not observation.runtime_enabled:
        reasons.append("runtime_not_enabled")
    if not observation.operator_shutdown_available:
        reasons.append("operator_shutdown_unavailable")
    if observation.deployment_kill_switch_active:
        reasons.append("deployment_kill_switch_active")
    if policy.require_capital_governance and not observation.capital_approved:
        reasons.append("capital_governance_not_approved")
    if policy.require_risk_governance and not observation.risk_approved:
        reasons.append("risk_governance_not_approved")
    if not observation.readiness_approved:
        reasons.append("production_readiness_not_approved")
    if not observation.lifecycle_validation_passed:
        reasons.append("lifecycle_validation_not_passed")
    if not observation.canary_completed:
        reasons.append("canary_not_completed")
    if not observation.soak_completed:
        reasons.append("soak_not_completed")
    if not observation.failure_testing_passed:
        reasons.append("failure_testing_not_passed")
    if not observation.security_secure:
        reasons.append("security_not_secure")
    if not observation.incident_recovery_verified:
        reasons.append("incident_recovery_not_verified")

    if observation.reconciliation_failures < 0:
        reasons.append("invalid_reconciliation_failures")
    elif observation.reconciliation_failures > policy.maximum_reconciliation_failures:
        reasons.append("reconciliation_failures_exceeded")

    for name, value in (
        ("daily_loss_percent", observation.daily_loss_percent),
        ("drawdown_percent", observation.drawdown_percent),
        ("error_rate_percent", observation.error_rate_percent),
        ("slippage_percent", observation.slippage_percent),
    ):
        if not _valid_decimal(value):
            reasons.append(f"invalid_{name}")

    if _valid_decimal(observation.daily_loss_percent) and observation.daily_loss_percent > policy.maximum_daily_loss_percent:
        reasons.append("daily_loss_exceeded")
    if _valid_decimal(observation.drawdown_percent) and observation.drawdown_percent > policy.maximum_drawdown_percent:
        reasons.append("drawdown_exceeded")
    if _valid_decimal(observation.error_rate_percent) and observation.error_rate_percent > policy.maximum_error_rate_percent:
        reasons.append("error_rate_exceeded")
    if _valid_decimal(observation.slippage_percent) and observation.slippage_percent > policy.maximum_slippage_percent:
        reasons.append("slippage_exceeded")

    return ProductionOperationAssessment(
        action=ProductionOperationAction.HALT if reasons else ProductionOperationAction.OPERATE,
        reasons=tuple(reasons),
        strategy_version_id=observation.strategy_version_id,
        strategy_fingerprint=observation.strategy_fingerprint,
    )
