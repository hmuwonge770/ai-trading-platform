from packages.autonomy.monitoring import (
    AlertSeverity,
    AutonomousExecutionMonitor,
    MonitoringPolicy,
    MonitoringStatus,
    RuntimeHealthSnapshot,
)
from packages.autonomy.observability import ExecutionAuditEvent, ExecutionAuditStatus


def event(status: ExecutionAuditStatus) -> ExecutionAuditEvent:
    return ExecutionAuditEvent.create(
        status=status,
        runtime_mode="enabled",
        client_order_id="client-1",
        strategy_version_id="strategy-1",
        strategy_fingerprint="fingerprint-1",
        authorization_hash="auth-1",
        risk_approved=status is ExecutionAuditStatus.SUBMITTED,
        occurred_at=1,
    )


def test_healthy_runtime_with_no_events_is_healthy() -> None:
    report = AutonomousExecutionMonitor().assess((), RuntimeHealthSnapshot())
    assert report.healthy
    assert report.observed_events == 0
    assert report.alerts == ()


def test_repeated_blocks_raise_warning() -> None:
    monitor = AutonomousExecutionMonitor(policy=MonitoringPolicy(repeated_block_threshold=3))
    report = monitor.assess(
        (event(ExecutionAuditStatus.BLOCKED),) * 3,
        RuntimeHealthSnapshot(),
    )
    assert report.status is MonitoringStatus.WARNING
    assert report.alerts[0].code == "repeated_blocks"
    assert report.alerts[0].severity is AlertSeverity.WARNING


def test_repeated_duplicates_raise_warning() -> None:
    monitor = AutonomousExecutionMonitor(policy=MonitoringPolicy(repeated_failure_threshold=2))
    report = monitor.assess(
        (event(ExecutionAuditStatus.DUPLICATE),) * 2,
        RuntimeHealthSnapshot(),
    )
    assert report.status is MonitoringStatus.WARNING
    assert report.alerts[0].code == "repeated_duplicates"


def test_unsafe_runtime_health_is_critical() -> None:
    report = AutonomousExecutionMonitor().assess(
        (),
        RuntimeHealthSnapshot(
            authorization_valid=False,
            adapter_healthy=False,
            reconciliation_healthy=False,
            accounting_healthy=False,
            kill_switch_enabled=True,
        ),
    )
    assert report.status is MonitoringStatus.CRITICAL
    assert {alert.code for alert in report.alerts} == {
        "authorization_invalid",
        "adapter_unhealthy",
        "reconciliation_unhealthy",
        "accounting_unhealthy",
        "kill_switch_enabled",
    }


def test_alert_sink_receives_immutable_alerts() -> None:
    alerts = []

    class Sink:
        def append(self, alert):
            alerts.append(alert)

    monitor = AutonomousExecutionMonitor(alert_sink=Sink())
    report = monitor.assess((), RuntimeHealthSnapshot(kill_switch_enabled=True))
    assert len(alerts) == 1
    assert alerts[0] == report.alerts[0]


def test_thresholds_must_be_positive() -> None:
    try:
        MonitoringPolicy(repeated_block_threshold=0)
    except ValueError as exc:
        assert "repeated_block_threshold" in str(exc)
    else:
        raise AssertionError("expected validation error")
