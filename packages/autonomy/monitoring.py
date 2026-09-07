"""Deterministic read-only monitoring for autonomous execution health."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from .observability import ExecutionAuditEvent, ExecutionAuditStatus


class AlertSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class MonitoringStatus(StrEnum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class RuntimeHealthSnapshot:
    """Current control-plane health supplied by the application."""

    authorization_valid: bool = True
    adapter_healthy: bool = True
    reconciliation_healthy: bool = True
    accounting_healthy: bool = True
    kill_switch_enabled: bool = False


@dataclass(frozen=True, slots=True)
class MonitoringPolicy:
    """Bounded thresholds for deterministic alert escalation."""

    repeated_block_threshold: int = 3
    repeated_failure_threshold: int = 2

    def __post_init__(self) -> None:
        if self.repeated_block_threshold < 1:
            raise ValueError("repeated_block_threshold must be positive")
        if self.repeated_failure_threshold < 1:
            raise ValueError("repeated_failure_threshold must be positive")


@dataclass(frozen=True, slots=True)
class MonitoringAlert:
    severity: AlertSeverity
    code: str
    message: str
    event_count: int


@dataclass(frozen=True, slots=True)
class MonitoringReport:
    status: MonitoringStatus
    alerts: tuple[MonitoringAlert, ...]
    observed_events: int

    @property
    def healthy(self) -> bool:
        return self.status is MonitoringStatus.HEALTHY


class MonitoringAlertSink(Protocol):
    """Append-only application-owned alert destination."""

    def append(self, alert: MonitoringAlert) -> None: ...


class AutonomousExecutionMonitor:
    """Assess autonomous execution health without changing trading state."""

    def __init__(
        self,
        *,
        policy: MonitoringPolicy | None = None,
        alert_sink: MonitoringAlertSink | None = None,
    ) -> None:
        self.policy = policy or MonitoringPolicy()
        self._alert_sink = alert_sink

    def assess(
        self,
        events: tuple[ExecutionAuditEvent, ...],
        health: RuntimeHealthSnapshot,
    ) -> MonitoringReport:
        alerts: list[MonitoringAlert] = []
        blocked = sum(event.status is ExecutionAuditStatus.BLOCKED for event in events)
        duplicates = sum(event.status is ExecutionAuditStatus.DUPLICATE for event in events)

        if not health.authorization_valid:
            alerts.append(MonitoringAlert(AlertSeverity.CRITICAL, "authorization_invalid", "live authorization is invalid or expired", len(events)))
        if not health.adapter_healthy:
            alerts.append(MonitoringAlert(AlertSeverity.CRITICAL, "adapter_unhealthy", "live exchange adapter healthcheck is unhealthy", len(events)))
        if not health.reconciliation_healthy:
            alerts.append(MonitoringAlert(AlertSeverity.CRITICAL, "reconciliation_unhealthy", "exchange reconciliation is unhealthy", len(events)))
        if not health.accounting_healthy:
            alerts.append(MonitoringAlert(AlertSeverity.CRITICAL, "accounting_unhealthy", "accounting reconciliation is unhealthy", len(events)))
        if health.kill_switch_enabled:
            alerts.append(MonitoringAlert(AlertSeverity.CRITICAL, "kill_switch_enabled", "autonomous execution is stopped by the kill switch", len(events)))
        if blocked >= self.policy.repeated_block_threshold:
            alerts.append(MonitoringAlert(AlertSeverity.WARNING, "repeated_blocks", "repeated execution blocks detected", blocked))
        if duplicates >= self.policy.repeated_failure_threshold:
            alerts.append(MonitoringAlert(AlertSeverity.WARNING, "repeated_duplicates", "repeated duplicate-order suppression detected", duplicates))

        for alert in alerts:
            if self._alert_sink is not None:
                self._alert_sink.append(alert)

        status = MonitoringStatus.HEALTHY
        if any(alert.severity is AlertSeverity.CRITICAL for alert in alerts):
            status = MonitoringStatus.CRITICAL
        elif alerts:
            status = MonitoringStatus.WARNING
        return MonitoringReport(status, tuple(alerts), len(events))
