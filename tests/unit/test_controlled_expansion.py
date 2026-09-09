from decimal import Decimal
from uuid import UUID

import pytest

from packages.autonomy.controlled_expansion import (
    ExpansionAction,
    ExpansionRequest,
    evaluate_expansion,
)
from packages.autonomy.controlled_expansion_ledger import InMemoryExpansionLedger


STRATEGY = UUID("12345678-1234-5678-1234-567812345678")


def request(**overrides):
    values = dict(
        strategy_version_id=STRATEGY,
        current_cohort_percent=Decimal("1"),
        requested_cohort_percent=Decimal("2"),
        soak_samples=1000,
        observed_error_rate_percent=Decimal("0.5"),
        observed_drawdown_percent=Decimal("1"),
        observed_slippage_percent=Decimal("0.5"),
        reconciliation_failures=0,
        canary_completed=True,
        soak_completed=True,
        promotion_approved=True,
        risk_approved=True,
        capital_approved=True,
        runtime_ready=True,
        kill_switch_clear=True,
        explicit_operator_approval=True,
    )
    values.update(overrides)
    return ExpansionRequest(**values)


def test_approved_one_percent_step_expands():
    report = evaluate_expansion(request())
    assert report.action is ExpansionAction.EXPAND
    assert report.safe
    assert report.approved_delta_percent == Decimal("1")


@pytest.mark.parametrize("field", ["canary_completed", "soak_completed", "promotion_approved", "risk_approved", "capital_approved", "runtime_ready", "kill_switch_clear"])
def test_missing_hard_gate_aborts(field):
    report = evaluate_expansion(request(**{field: False}))
    assert report.action is ExpansionAction.ABORT
    assert not report.should_expand


def test_operator_approval_missing_holds():
    report = evaluate_expansion(request(explicit_operator_approval=False))
    assert report.action is ExpansionAction.HOLD
    assert "operator_approval_required" in report.reasons


@pytest.mark.parametrize("kwargs", [
    {"requested_cohort_percent": Decimal("3.1")},
    {"requested_cohort_percent": Decimal("6")},
])
def test_expansion_cannot_exceed_step_or_ceiling(kwargs):
    with pytest.raises(ValueError):
        evaluate_expansion(request(**kwargs))


def test_negative_and_nonfinite_values_fail_closed():
    with pytest.raises(ValueError):
        evaluate_expansion(request(current_cohort_percent=Decimal("-1")))
    with pytest.raises(ValueError):
        evaluate_expansion(request(requested_cohort_percent="NaN"))


def test_bad_observation_aborts():
    report = evaluate_expansion(request(observed_error_rate_percent=Decimal("1.01")))
    assert report.action is ExpansionAction.ABORT
    assert "error_rate_exceeded" in report.reasons


def test_zero_delta_holds():
    report = evaluate_expansion(request(requested_cohort_percent=Decimal("1")))
    assert report.action is ExpansionAction.HOLD
    assert "no_expansion_requested" in report.reasons


def test_ledger_is_idempotent_and_identity_bound():
    report = evaluate_expansion(request())
    ledger = InMemoryExpansionLedger()
    first = ledger.record(strategy_version_id=STRATEGY, request_key="run-1", report=report)
    second = ledger.record(strategy_version_id=STRATEGY, request_key="run-1", report=report)
    assert first == second
    with pytest.raises(ValueError, match="different expansion decision"):
        ledger.record(strategy_version_id=STRATEGY, request_key="run-1", report=evaluate_expansion(request(requested_cohort_percent=Decimal("1"))))
