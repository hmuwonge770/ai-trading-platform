"""AY full autonomous lifecycle validation.

Control-plane validation only. This module never activates live execution,
submits exchange orders, changes capital/risk ceilings, or bypasses safety gates.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class LifecycleValidationAction(StrEnum):
    PASS = "pass"
    HOLD = "hold"
    BLOCK = "block"


@dataclass(frozen=True, slots=True)
class LifecycleValidationObservation:
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


@dataclass(frozen=True, slots=True)
class LifecycleValidationAssessment:
    action: LifecycleValidationAction
    safe: bool
    reasons: tuple[str, ...]


_REQUIRED = (
    ("promotion_not_approved", "promotion_approved"),
    ("canary_not_completed", "canary_completed"),
    ("soak_not_completed", "soak_completed"),
    ("expansion_not_validated", "expansion_validated"),
    ("incident_recovery_not_verified", "incident_recovery_verified"),
    ("retirement_not_validated", "retirement_validated"),
    ("risk_not_approved", "risk_approved"),
    ("capital_not_approved", "capital_approved"),
    ("runtime_not_ready", "runtime_ready"),
    ("deployment_kill_switch_active", "kill_switch_clear"),
    ("operator_approval_missing", "operator_approval"),
)


def validate_lifecycle(observation: LifecycleValidationObservation) -> LifecycleValidationAssessment:
    """Evaluate the complete lifecycle deterministically without executing it."""
    reasons = tuple(reason for reason, attribute in _REQUIRED if not getattr(observation, attribute))

    if not observation.strategy_identity_verified:
        return LifecycleValidationAssessment(
            LifecycleValidationAction.BLOCK,
            False,
            ("strategy_identity_mismatch", *reasons),
        )

    critical = {
        "promotion_not_approved",
        "canary_not_completed",
        "soak_not_completed",
        "incident_recovery_not_verified",
        "risk_not_approved",
        "capital_not_approved",
        "runtime_not_ready",
        "deployment_kill_switch_active",
    }
    if any(reason in critical for reason in reasons):
        return LifecycleValidationAssessment(LifecycleValidationAction.BLOCK, False, reasons)
    if reasons:
        return LifecycleValidationAssessment(LifecycleValidationAction.HOLD, True, reasons)
    return LifecycleValidationAssessment(LifecycleValidationAction.PASS, True, ())
