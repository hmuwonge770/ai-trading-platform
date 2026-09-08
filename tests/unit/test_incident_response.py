from packages.autonomy.incident_response import (
    AutonomousIncidentResponse,
    IncidentObservation,
    IncidentResponseAction,
    IncidentResponseSeverity,
)


def observation(**overrides):
    values = dict(
        incident_id="incident-1",
        fingerprint="fp-1",
        code="adapter_timeout",
        severity=IncidentResponseSeverity.WARNING,
        observed_at=1_000,
    )
    values.update(overrides)
    return IncidentObservation(**values)


def test_warning_is_contained():
    report = AutonomousIncidentResponse().evaluate(observation())
    assert report.action is IncidentResponseAction.CONTAIN
    assert report.may_contain


def test_info_requires_no_action():
    report = AutonomousIncidentResponse().evaluate(observation(severity=IncidentResponseSeverity.INFO))
    assert report.action is IncidentResponseAction.NO_ACTION


def test_critical_health_failure_aborts():
    report = AutonomousIncidentResponse().evaluate(observation(reconciliation_healthy=False))
    assert report.action is IncidentResponseAction.ABORT
    assert not report.safe
    assert "reconciliation_unhealthy" in report.reasons


def test_kill_switch_always_aborts():
    report = AutonomousIncidentResponse().evaluate(observation(kill_switch_enabled=True))
    assert report.action is IncidentResponseAction.ABORT
    assert not report.safe


def test_repeated_incident_escalates():
    report = AutonomousIncidentResponse().evaluate(observation(repeated_count=3))
    assert report.action is IncidentResponseAction.ESCALATE
    assert report.safe
    assert report.requires_escalation


def test_recovery_limit_aborts():
    report = AutonomousIncidentResponse().evaluate(observation(recovery_attempts=2))
    assert report.action is IncidentResponseAction.ABORT
    assert not report.safe


def test_incomplete_evidence_aborts():
    report = AutonomousIncidentResponse().evaluate(observation(evidence_complete=False))
    assert report.action is IncidentResponseAction.ABORT


def test_invalid_identity_rejected():
    import pytest

    with pytest.raises(ValueError):
        observation(incident_id="")


def test_negative_counter_rejected():
    import pytest

    with pytest.raises(ValueError):
        observation(repeated_count=-1)


def test_evaluation_is_deterministic():
    item = observation(repeated_count=1)
    first = AutonomousIncidentResponse().evaluate(item)
    second = AutonomousIncidentResponse().evaluate(item)
    assert first == second
