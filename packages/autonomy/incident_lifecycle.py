"""Deterministic operational incident lifecycle for autonomous trading."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class IncidentStatus(StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    ESCALATED = "escalated"
    RESOLVED = "resolved"


class IncidentSeverity(StrEnum):
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class Incident:
    incident_id: str
    fingerprint: str
    severity: IncidentSeverity
    code: str
    opened_at: int
    status: IncidentStatus = IncidentStatus.OPEN
    acknowledged_at: int | None = None
    resolved_at: int | None = None

    def __post_init__(self) -> None:
        if not self.incident_id.strip() or not self.fingerprint.strip() or not self.code.strip():
            raise ValueError("incident identity must not be empty")
        if self.opened_at <= 0:
            raise ValueError("opened_at must be positive")
        if self.acknowledged_at is not None and self.acknowledged_at < self.opened_at:
            raise ValueError("acknowledged_at cannot precede opened_at")
        if self.resolved_at is not None and self.resolved_at < self.opened_at:
            raise ValueError("resolved_at cannot precede opened_at")
        if self.status is IncidentStatus.ACKNOWLEDGED and self.acknowledged_at is None:
            raise ValueError("acknowledged incidents require acknowledged_at")
        if self.status is IncidentStatus.RESOLVED and self.resolved_at is None:
            raise ValueError("resolved incidents require resolved_at")


class IncidentStore(Protocol):
    """Application-owned durable incident persistence capability."""

    def save(self, incident: Incident) -> None: ...

    def get(self, incident_id: str) -> Incident | None: ...


class IncidentLifecycle:
    """Apply monotonic incident transitions without trading authority."""

    _TRANSITIONS = {
        IncidentStatus.OPEN: {IncidentStatus.ACKNOWLEDGED, IncidentStatus.ESCALATED, IncidentStatus.RESOLVED},
        IncidentStatus.ACKNOWLEDGED: {IncidentStatus.ESCALATED, IncidentStatus.RESOLVED},
        IncidentStatus.ESCALATED: {IncidentStatus.RESOLVED},
        IncidentStatus.RESOLVED: set(),
    }

    def __init__(self, *, store: IncidentStore) -> None:
        self._store = store

    def transition(self, incident: Incident, status: IncidentStatus, *, occurred_at: int) -> Incident:
        if occurred_at < incident.opened_at:
            raise ValueError("transition timestamp cannot precede incident opening")
        if status not in self._TRANSITIONS[incident.status]:
            raise ValueError(f"invalid incident transition: {incident.status.value}->{status.value}")
        updated = Incident(
            incident_id=incident.incident_id,
            fingerprint=incident.fingerprint,
            severity=incident.severity,
            code=incident.code,
            opened_at=incident.opened_at,
            status=status,
            acknowledged_at=occurred_at if status is IncidentStatus.ACKNOWLEDGED else incident.acknowledged_at,
            resolved_at=occurred_at if status is IncidentStatus.RESOLVED else incident.resolved_at,
        )
        self._store.save(updated)
        return updated
