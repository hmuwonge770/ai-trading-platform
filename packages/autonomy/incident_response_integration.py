"""Read-only composition boundary for autonomous incident response."""

from __future__ import annotations

from dataclasses import dataclass

from .incident_response import AutonomousIncidentResponse, IncidentResponsePolicy, IncidentResponseReport
from .incident_response_detection import AutonomousIncidentDetector, IncidentDetectionReport


@dataclass(frozen=True, slots=True)
class IncidentResponseContext:
    """Upstream operational facts; this object carries no execution authority."""

    authorization_valid: bool
    adapter_healthy: bool
    reconciliation_healthy: bool
    accounting_healthy: bool
    kill_switch_enabled: bool


@dataclass(frozen=True, slots=True)
class IncidentResponseDecision:
    detection: IncidentDetectionReport
    response: IncidentResponseReport


class AutonomousIncidentResponseIntegration:
    """Compose incident detection and bounded response planning without mutation."""

    def __init__(
        self,
        *,
        detector: AutonomousIncidentDetector | None = None,
        responder: AutonomousIncidentResponse | None = None,
    ) -> None:
        self.detector = detector or AutonomousIncidentDetector()
        self.responder = responder or AutonomousIncidentResponse(policy=IncidentResponsePolicy())

    def evaluate(
        self,
        *,
        incident_id: str,
        fingerprint: str,
        code: str,
        observed_at: int,
        context: IncidentResponseContext,
        repeated_count: int = 0,
        recovery_attempts: int = 0,
        evidence_complete: bool = True,
    ) -> IncidentResponseDecision:
        detection = self.detector.detect(
            incident_id=incident_id,
            fingerprint=fingerprint,
            code=code,
            observed_at=observed_at,
            authorization_valid=context.authorization_valid,
            adapter_healthy=context.adapter_healthy,
            reconciliation_healthy=context.reconciliation_healthy,
            accounting_healthy=context.accounting_healthy,
            kill_switch_enabled=context.kill_switch_enabled,
            repeated_count=repeated_count,
            recovery_attempts=recovery_attempts,
            evidence_complete=evidence_complete,
        )
        response = self.responder.evaluate(detection.observation)
        if context.kill_switch_enabled and response.action is not response.action.ABORT:
            raise AssertionError("incident response cannot bypass an active kill switch")
        return IncidentResponseDecision(detection, response)
