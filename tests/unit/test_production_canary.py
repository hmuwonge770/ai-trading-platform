from decimal import Decimal
from uuid import UUID

import pytest

from packages.autonomy.production_canary import (
    AutonomousProductionCanaryGovernance,
    ProductionCanaryAction,
    ProductionCanaryPolicy,
    ProductionCanaryRequest,
)


STRATEGY_ID = UUID("12345678-1234-5678-1234-567812345678")


def request(**overrides):
    values = dict(
        strategy_version_id=STRATEGY_ID,
        requested_cohort_percent=Decimal("100"),
        evidence_samples=100,
        observed_error_rate_percent=Decimal("0"),
        reconciliation_failures=0,
        observed_drawdown_percent=Decimal("0"),
        observed_slippage_percent=Decimal("0"),
        promotion_approved=True,
        risk_approved=True,
        capital_approved=True,
        runtime_ready=True,
        kill_switch_clear=True,
        explicit_operator_approval=True,
    )
    values.update(overrides)
    return ProductionCanaryRequest(**values)


def test_ready_request_starts_when_assigned():
    report = AutonomousProductionCanaryGovernance().evaluate(request())
    assert report.action is ProductionCanaryAction.START
    assert report.should_start
    assert report.safe
    assert report.assigned_to_cohort


def test_operator_approval_is_required_and_holds():
    report = AutonomousProductionCanaryGovernance().evaluate(request(explicit_operator_approval=False))
    assert report.action is ProductionCanaryAction.HOLD
    assert "operator_approval_required" in report.reasons


@pytest.mark.parametrize("field", ["promotion_approved", "risk_approved", "capital_approved", "runtime_ready", "kill_switch_clear"])
def test_safety_gate_failure_aborts(field):
    report = AutonomousProductionCanaryGovernance().evaluate(request(**{field: False}))
    assert report.action is ProductionCanaryAction.ABORT
    assert not report.should_start


def test_evidence_and_observations_hold_or_abort_with_bounded_policy():
    policy = ProductionCanaryPolicy(
        minimum_evidence_samples=200,
        max_error_rate_percent=Decimal("1"),
        max_drawdown_percent=Decimal("2"),
        max_slippage_percent=Decimal("1"),
    )
    governance = AutonomousProductionCanaryGovernance(policy=policy)
    report = governance.evaluate(request(evidence_samples=100))
    assert report.action is ProductionCanaryAction.HOLD
    assert "insufficient_evidence" in report.reasons

    report = governance.evaluate(request(observed_error_rate_percent=Decimal("1.01")))
    assert report.action is ProductionCanaryAction.ABORT
    assert "error_rate_exceeded" in report.reasons


def test_requested_cohort_cannot_exceed_policy():
    governance = AutonomousProductionCanaryGovernance(
        policy=ProductionCanaryPolicy(max_cohort_percent=Decimal("1"))
    )
    with pytest.raises(ValueError, match="approved canary boundary"):
        governance.evaluate(request(requested_cohort_percent=Decimal("2")))


def test_negative_and_non_finite_values_fail_closed():
    governance = AutonomousProductionCanaryGovernance()
    with pytest.raises(ValueError):
        governance.evaluate(request(requested_cohort_percent=Decimal("-1")))
    with pytest.raises(ValueError):
        governance.evaluate(request(observed_slippage_percent="NaN"))


def test_cohort_assignment_is_deterministic():
    governance = AutonomousProductionCanaryGovernance()
    first = governance.evaluate(request(requested_cohort_percent=Decimal("50")))
    second = governance.evaluate(request(requested_cohort_percent=Decimal("50")))
    assert first == second


def test_governance_is_read_only():
    policy = ProductionCanaryPolicy()
    governance = AutonomousProductionCanaryGovernance(policy=policy)
    before = governance.policy
    governance.evaluate(request())
    assert governance.policy == before


def test_reconciliation_failure_aborts():
    report = AutonomousProductionCanaryGovernance().evaluate(request(reconciliation_failures=1))
    assert report.action is ProductionCanaryAction.ABORT
    assert "reconciliation_failures_exceeded" in report.reasons
