from datetime import timedelta
from decimal import Decimal
import pytest

from packages.autonomy.operational_slos import OperationalObservation, OperationalSLOPolicy, SLOStatus
from packages.autonomy.operational_slos_governance import AutonomousOperationalSLOGovernance
from packages.autonomy.operational_slos_integration import AutonomousOperationalSLOIntegration, OperationalGovernanceContext


def obs(**overrides):
    values = dict(
        availability_percent=Decimal("99.9"), decision_latency_ms=Decimal("200"),
        reconciliation_latency_ms=Decimal("1000"), error_rate_percent=Decimal("0.1"),
        queue_depth=100, active_workers=8, worker_capacity=16, window=timedelta(seconds=600),
    )
    values.update(overrides)
    return OperationalObservation(**values)


def test_healthy_observation():
    report = AutonomousOperationalSLOGovernance().evaluate(obs())
    assert report.status is SLOStatus.HEALTHY
    assert report.safe_to_continue

@pytest.mark.parametrize("field,value,reason", [
    ("availability_percent", Decimal("98"), "availability_slo_breached"),
    ("decision_latency_ms", Decimal("2000"), "decision_latency_slo_breached"),
    ("reconciliation_latency_ms", Decimal("6000"), "reconciliation_latency_slo_breached"),
    ("error_rate_percent", Decimal("2"), "error_rate_slo_breached"),
    ("queue_depth", 1001, "queue_depth_capacity_breached"),
    ("active_workers", 33, "worker_concurrency_breached"),
    ("active_workers", 14, "capacity_headroom_breached"),
])
def test_thresholds_breach(field, value, reason):
    report = AutonomousOperationalSLOGovernance().evaluate(obs(**{field: value}))
    assert report.status is SLOStatus.BREACHED
    assert reason in report.reasons


def test_short_window_is_at_risk():
    report = AutonomousOperationalSLOGovernance().evaluate(obs(window=timedelta(seconds=60)))
    assert report.status is SLOStatus.AT_RISK
    assert "insufficient_observation_window" in report.reasons

@pytest.mark.parametrize("field,value", [
    ("availability_percent", Decimal("NaN")),
    ("decision_latency_ms", Decimal("Infinity")),
    ("error_rate_percent", Decimal("-1")),
])
def test_invalid_observations_fail_closed(field, value):
    with pytest.raises(ValueError):
        obs(**{field: value})


def test_integration_blocks_on_hard_safety_context():
    report = AutonomousOperationalSLOIntegration().evaluate(
        obs(), OperationalGovernanceContext(kill_switch_clear=False, runtime_enabled=True, authorization_valid=True)
    )
    assert report.status is SLOStatus.BLOCKED
    assert "kill_switch_active" in report.reasons


def test_integration_is_deterministic_and_read_only():
    integration = AutonomousOperationalSLOIntegration()
    context = OperationalGovernanceContext(True, True, True)
    first = integration.evaluate(obs(), context)
    second = integration.evaluate(obs(), context)
    assert first == second
    assert first.status is SLOStatus.HEALTHY


def test_policy_rejects_invalid_values():
    with pytest.raises(ValueError):
        OperationalSLOPolicy(max_queue_depth=-1)
    with pytest.raises(ValueError):
        OperationalSLOPolicy(max_error_rate_percent=Decimal("Infinity"))
