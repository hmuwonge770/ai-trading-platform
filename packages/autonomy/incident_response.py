"""Deterministic, fail-closed autonomous incident response governance."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite


class IncidentResponseAction(StrEnum):
    NO_ACTION = "no_action"
    CONTAIN = "contain"
    ESCALATE = "escalate"
    ABORT = "abort"


class IncidentResponseSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class IncidentObservation:
    incident_id: str
    fingerprint: str
    code: str
    severity: IncidentResponseSeverity
    observed_at: int
    authorization_valid: bool = True
    adapter_healthy: bool = True
    reconciliation_healthy: bool = True
    accounting_healthy: bool = True
    kill_switch_enabled: bool = False
    repeated_count: int = 0
    recovery_attempts: int = 0
    evidence_complete: bool = True

    def __post_init__(self) -> None:
        if not self.incident_id.strip() or not self.fingerprint.strip() or not self.code.strip():
            raise ValueError("incident identity must not be empty")
        if self.observed_at <= 0:
            raise ValueError("observed_at must be positive")
        if self.repeated_count < 0 or self.recovery_attempts < 0:
            raise ValueError("incident counters cannot be negative")


@dataclass(frozen=True, slots=True)
class IncidentResponsePolicy:
    repeated_incident_threshold: int = 3
    maximum_recovery_attempts: int = 2

    def __post_init__(self) -> None:
        if self.repeated_incident_threshold < 1:
            raise ValueError("repeated_incident_threshold must be positive")
        if self.maximum_recovery_attempts < 0:
            raise ValueError("maximum_recovery_attempts cannot be negative")


@dataclass(frozen=True, slots=True)
class IncidentResponseReport:
    incident_id: str
    fingerprint: str
    action: IncidentResponseAction
    safe: bool
    reasons: tuple[str, ...]

    @property
    def may_contain(self) -> bool:
        return self.action is IncidentResponseAction.CONTAIN and self.safe

    @property
    def requires_escalation(self) -> bool:
        return self.action in {IncidentResponseAction.ESCALATE, IncidentResponseAction.ABORT}


class AutonomousIncidentResponse:
    """Plan bounded incident handling without executing trading operations."""

    def __init__(self, *, policy: IncidentResponsePolicy | None = None) -> None:
        self.policy = policy or IncidentResponsePolicy()

    def evaluate(self, observation: IncidentObservation) -> IncidentResponseReport:
        reasons: list[str] = []
        critical = False

        if observation.kill_switch_enabled:
            reasons.append("kill_switch_enabled")
            critical = True
        if not observation.authorization_valid:
            reasons.append("authorization_invalid")
            critical = True
        if not observation.adapter_healthy:
            reasons.append("adapter_unhealthy")
            critical = True
        if not observation.reconciliation_healthy:
            reasons.append("reconciliation_unhealthy")
            critical = True
        if not observation.accounting_healthy:
            reasons.append("accounting_unhealthy")
            critical = True
        if not observation.evidence_complete:
            reasons.append("incomplete_incident_evidence")
            critical = True
        if observation.recovery_attempts >= self.policy.maximum_recovery_attempts and observation.recovery_attempts > 0:
            reasons.append("recovery_attempt_limit_reached")
            critical = True
        if observation.repeated_count >= self.policy.repeated_incident_threshold:
            reasons.append("repeated_incident_threshold_reached")
            return IncidentResponseReport(observation.incident_id, observation.fingerprint, IncidentResponseAction.ESCALATE, True, tuple(reasons))
        if critical:
            return IncidentResponseReport(observation.incident_id, observation.fingerprint, IncidentResponseAction.ABORT, False, tuple(reasons))
        if observation.severity is IncidentResponseSeverity.CRITICAL:
            reasons.append("critical_incident")
            return IncidentResponseReport(observation.incident_id, observation.fingerprint, IncidentResponseAction.CONTAIN, True, tuple(reasons))
        if observation.severity is IncidentResponseSeverity.WARNING:
            reasons.append("warning_incident")
            return IncidentResponseReport(observation.incident_id, observation.fingerprint, IncidentResponseAction.CONTAIN, True, tuple(reasons))
        return IncidentResponseReport(observation.incident_id, observation.fingerprint, IncidentResponseAction.NO_ACTION, True, tuple(reasons))
