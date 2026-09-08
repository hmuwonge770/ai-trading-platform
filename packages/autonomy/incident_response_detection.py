"""Deterministic classification of operational failures into incidents."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .incident_response import IncidentObservation, IncidentResponseSeverity


class IncidentSignal(StrEnum):
    AUTHORIZATION = "authorization"
    ADAPTER = "adapter"
    RECONCILIATION = "reconciliation"
    ACCOUNTING = "accounting"
    KILL_SWITCH = "kill_switch"
    EVIDENCE = "evidence"
    RECOVERY = "recovery"


@dataclass(frozen=True, slots=True)
class IncidentDetectionReport:
    observation: IncidentObservation
    signals: tuple[IncidentSignal, ...]


class AutonomousIncidentDetector:
    """Turn supplied health facts into a stable, typed incident observation."""

    def detect(
        self,
        *,
        incident_id: str,
        fingerprint: str,
        code: str,
        observed_at: int,
        authorization_valid: bool,
        adapter_healthy: bool,
        reconciliation_healthy: bool,
        accounting_healthy: bool,
        kill_switch_enabled: bool,
        repeated_count: int = 0,
        recovery_attempts: int = 0,
        evidence_complete: bool = True,
    ) -> IncidentDetectionReport:
        signals: list[IncidentSignal] = []
        if not authorization_valid:
            signals.append(IncidentSignal.AUTHORIZATION)
        if not adapter_healthy:
            signals.append(IncidentSignal.ADAPTER)
        if not reconciliation_healthy:
            signals.append(IncidentSignal.RECONCILIATION)
        if not accounting_healthy:
            signals.append(IncidentSignal.ACCOUNTING)
        if kill_switch_enabled:
            signals.append(IncidentSignal.KILL_SWITCH)
        if not evidence_complete:
            signals.append(IncidentSignal.EVIDENCE)
        if recovery_attempts:
            signals.append(IncidentSignal.RECOVERY)
        severity = IncidentResponseSeverity.CRITICAL if signals else IncidentResponseSeverity.INFO
        observation = IncidentObservation(
            incident_id=incident_id,
            fingerprint=fingerprint,
            code=code,
            severity=severity,
            observed_at=observed_at,
            authorization_valid=authorization_valid,
            adapter_healthy=adapter_healthy,
            reconciliation_healthy=reconciliation_healthy,
            accounting_healthy=accounting_healthy,
            kill_switch_enabled=kill_switch_enabled,
            repeated_count=repeated_count,
            recovery_attempts=recovery_attempts,
            evidence_complete=evidence_complete,
        )
        return IncidentDetectionReport(observation, tuple(signals))
