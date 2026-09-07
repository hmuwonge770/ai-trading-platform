"""Credential-free operational delivery boundary for autonomous alerts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class AlertSeverity(StrEnum):
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class OperationalAlert:
    alert_id: str
    severity: AlertSeverity
    code: str
    message: str
    occurred_at: int
    dedupe_key: str

    def __post_init__(self) -> None:
        if not self.alert_id.strip() or not self.code.strip() or not self.message.strip():
            raise ValueError("alert identity and message must not be empty")
        if self.occurred_at <= 0:
            raise ValueError("occurred_at must be positive")
        if not self.dedupe_key.strip():
            raise ValueError("dedupe_key must not be empty")


class OperationalAlertSink(Protocol):
    """External notification capability; implementations own delivery only."""

    def deliver(self, alert: OperationalAlert) -> None: ...


class AlertDeliveryStatus(StrEnum):
    DELIVERED = "delivered"
    SUPPRESSED = "suppressed"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class AlertDeliveryReport:
    status: AlertDeliveryStatus
    alert: OperationalAlert
    reason: str | None = None


class AutonomousAlertDelivery:
    """Deliver operational alerts with deterministic duplicate suppression."""

    def __init__(self, *, sink: OperationalAlertSink, max_recent_keys: int = 1024) -> None:
        if max_recent_keys <= 0:
            raise ValueError("max_recent_keys must be positive")
        self._sink = sink
        self._max_recent_keys = max_recent_keys
        self._recent_keys: list[str] = []
        self._recent_set: set[str] = set()

    def deliver(self, alert: OperationalAlert) -> AlertDeliveryReport:
        if alert.dedupe_key in self._recent_set:
            return AlertDeliveryReport(AlertDeliveryStatus.SUPPRESSED, alert, "duplicate_alert")
        try:
            self._sink.deliver(alert)
        except Exception:
            return AlertDeliveryReport(AlertDeliveryStatus.BLOCKED, alert, "delivery_failed")
        self._remember(alert.dedupe_key)
        return AlertDeliveryReport(AlertDeliveryStatus.DELIVERED, alert)

    def _remember(self, key: str) -> None:
        self._recent_keys.append(key)
        self._recent_set.add(key)
        if len(self._recent_keys) > self._max_recent_keys:
            expired = self._recent_keys.pop(0)
            self._recent_set.discard(expired)
