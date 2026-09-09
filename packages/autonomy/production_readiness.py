"""Deterministic production-readiness assessment for autonomous trading.

AW is a control-plane gate. It does not enable live execution, change limits,
handle exchange credentials, or submit orders.
"""
from dataclasses import dataclass
from enum import StrEnum


class ReadinessStatus(StrEnum):
    READY = "ready"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class ProductionReadinessPolicy:
    require_soak_evidence: bool = True
    require_failure_evidence: bool = True
    require_slo_evidence: bool = True
    require_security_evidence: bool = True
    require_incident_recovery_evidence: bool = True
    require_operator_approval: bool = True
    require_runtime_preflight: bool = True


@dataclass(frozen=True, slots=True)
class ProductionReadinessObservation:
    soak_complete: bool
    failure_testing_complete: bool
    slo_healthy: bool
    security_secure: bool
    incident_recovery_verified: bool
    operator_approved: bool
    runtime_preflight_passed: bool
    strategy_id: str
    strategy_version: str


@dataclass(frozen=True, slots=True)
class ProductionReadinessAssessment:
    status: ReadinessStatus
    reasons: tuple[str, ...]


def assess_production_readiness(
    observation: ProductionReadinessObservation,
    policy: ProductionReadinessPolicy | None = None,
) -> ProductionReadinessAssessment:
    """Evaluate all production prerequisites deterministically and fail closed."""
    policy = policy or ProductionReadinessPolicy()
    if not observation.strategy_id or not observation.strategy_version:
        return ProductionReadinessAssessment(
            ReadinessStatus.BLOCKED, ("strategy_identity_missing",)
        )

    checks = (
        (policy.require_soak_evidence, observation.soak_complete, "soak_evidence_missing"),
        (policy.require_failure_evidence, observation.failure_testing_complete, "failure_testing_missing"),
        (policy.require_slo_evidence, observation.slo_healthy, "slo_evidence_not_healthy"),
        (policy.require_security_evidence, observation.security_secure, "security_evidence_not_secure"),
        (policy.require_incident_recovery_evidence, observation.incident_recovery_verified, "incident_recovery_not_verified"),
        (policy.require_operator_approval, observation.operator_approved, "operator_approval_missing"),
        (policy.require_runtime_preflight, observation.runtime_preflight_passed, "runtime_preflight_failed"),
    )
    reasons = tuple(reason for required, passed, reason in checks if required and not passed)
    if reasons:
        return ProductionReadinessAssessment(ReadinessStatus.BLOCKED, reasons)
    return ProductionReadinessAssessment(ReadinessStatus.READY, ())
