"""Governance integration for AY lifecycle validation."""
from __future__ import annotations

from dataclasses import dataclass

from .autonomous_lifecycle_validation import (
    LifecycleValidationAssessment,
    LifecycleValidationObservation,
    validate_lifecycle,
)


@dataclass(frozen=True, slots=True)
class LifecycleValidationContext:
    strategy_identity_verified: bool
    promotion_approved: bool
    canary_completed: bool
    soak_completed: bool
    expansion_validated: bool
    incident_recovery_verified: bool
    retirement_validated: bool
    risk_approved: bool
    capital_approved: bool
    runtime_ready: bool
    kill_switch_clear: bool
    operator_approval: bool


class AutonomousLifecycleValidationIntegration:
    """Compose lifecycle evidence without mutating any upstream subsystem."""

    def assess(self, context: LifecycleValidationContext) -> LifecycleValidationAssessment:
        observation = LifecycleValidationObservation(
            strategy_identity_verified=context.strategy_identity_verified,
            promotion_approved=context.promotion_approved,
            canary_completed=context.canary_completed,
            soak_completed=context.soak_completed,
            expansion_validated=context.expansion_validated,
            incident_recovery_verified=context.incident_recovery_verified,
            retirement_validated=context.retirement_validated,
            risk_approved=context.risk_approved,
            capital_approved=context.capital_approved,
            runtime_ready=context.runtime_ready,
            kill_switch_clear=context.kill_switch_clear,
            operator_approval=context.operator_approval,
        )
        return validate_lifecycle(observation)
