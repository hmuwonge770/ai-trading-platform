"""Governance integration for the final AZ production-operation gate."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .production_operation import (
    ProductionOperationAssessment,
    ProductionOperationObservation,
    assess_production_operation,
)


@dataclass(frozen=True, slots=True)
class ProductionOperationContext:
    """Immutable upstream evidence supplied by already-authorized subsystems."""

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


class AutonomousProductionOperationIntegration:
    """Compose upstream evidence without activating runtime or submitting orders."""

    def assess(self, context: ProductionOperationContext) -> ProductionOperationAssessment:
        observation = ProductionOperationObservation(
            strategy_version_id=context.strategy_version_id,
            strategy_fingerprint=context.strategy_fingerprint,
            live_authorized=context.live_authorized,
            runtime_enabled=context.runtime_enabled,
            operator_shutdown_available=context.operator_shutdown_available,
            deployment_kill_switch_active=context.deployment_kill_switch_active,
            capital_approved=context.capital_approved,
            risk_approved=context.risk_approved,
            readiness_approved=context.readiness_approved,
            lifecycle_validation_passed=context.lifecycle_validation_passed,
            canary_completed=context.canary_completed,
            soak_completed=context.soak_completed,
            failure_testing_passed=context.failure_testing_passed,
            security_secure=context.security_secure,
            incident_recovery_verified=context.incident_recovery_verified,
            reconciliation_failures=context.reconciliation_failures,
            daily_loss_percent=context.daily_loss_percent,
            drawdown_percent=context.drawdown_percent,
            error_rate_percent=context.error_rate_percent,
            slippage_percent=context.slippage_percent,
        )
        return assess_production_operation(observation)
