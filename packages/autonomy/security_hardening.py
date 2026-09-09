"""Deterministic security-hardening contracts for autonomous trading."""
from dataclasses import dataclass
from enum import StrEnum


class SecurityStatus(StrEnum):
    SECURE = "secure"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class SecurityHardeningPolicy:
    require_secret_isolation: bool = True
    require_signed_strategy_artifacts: bool = True
    require_audit_integrity: bool = True
    require_dependency_integrity: bool = True
    require_operator_shutdown: bool = True


@dataclass(frozen=True, slots=True)
class SecurityObservation:
    secrets_isolated: bool
    strategy_artifact_verified: bool
    audit_integrity_verified: bool
    dependencies_verified: bool
    operator_shutdown_available: bool
    identity_verified: bool


@dataclass(frozen=True, slots=True)
class SecurityAssessment:
    status: SecurityStatus
    reasons: tuple[str, ...]


def assess_security(
    policy: SecurityHardeningPolicy,
    observation: SecurityObservation,
) -> SecurityAssessment:
    reasons: list[str] = []
    checks = (
        (policy.require_secret_isolation, observation.secrets_isolated, "secret_isolation_failed"),
        (policy.require_signed_strategy_artifacts, observation.strategy_artifact_verified, "strategy_artifact_verification_failed"),
        (policy.require_audit_integrity, observation.audit_integrity_verified, "audit_integrity_failed"),
        (policy.require_dependency_integrity, observation.dependencies_verified, "dependency_integrity_failed"),
        (policy.require_operator_shutdown, observation.operator_shutdown_available, "operator_shutdown_unavailable"),
    )
    if not observation.identity_verified:
        reasons.append("identity_verification_failed")
    reasons.extend(reason for required, passed, reason in checks if required and not passed)
    return SecurityAssessment(
        status=SecurityStatus.BLOCKED if reasons else SecurityStatus.SECURE,
        reasons=tuple(reasons),
    )
