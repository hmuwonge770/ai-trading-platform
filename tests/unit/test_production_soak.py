from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from packages.autonomy.production_soak import ProductionSoakEvidence, build_evidence_digest
from packages.autonomy.production_soak_governance import AutonomousProductionSoakGovernance, ProductionSoakAction
from packages.autonomy.production_soak_integration import AutonomousProductionSoakIntegration

START = datetime(2026, 9, 1, tzinfo=timezone.utc)
NOW = START + timedelta(days=1, minutes=5)


def evidence(**overrides):
    values = dict(
        strategy_version_id=UUID("11111111-1111-1111-1111-111111111111"),
        canary_run_id=UUID("22222222-2222-2222-2222-222222222222"),
        cohort_percent=Decimal("1"), started_at=START,
        ended_at=START + timedelta(days=1), collected_at=START + timedelta(days=1, minutes=1),
        samples=1000, observed_error_rate_percent=Decimal("0.2"), reconciliation_failures=0,
        observed_drawdown_percent=Decimal("1"), observed_slippage_percent=Decimal("0.5"),
        missing_intervals=0, evidence_digest="0" * 64,
    )
    values.update(overrides)
    item = ProductionSoakEvidence(**values)
    return replace(item, evidence_digest=build_evidence_digest(item))


def evaluate(item, **kwargs):
    defaults = dict(
        expected_strategy_version_id=item.strategy_version_id,
        expected_canary_run_id=item.canary_run_id,
        canary_completed=True, promotion_approved=True, risk_approved=True,
        capital_approved=True, runtime_ready=True, kill_switch_clear=True, now=NOW,
    )
    defaults.update(kwargs)
    return AutonomousProductionSoakGovernance().evaluate(item, **defaults)


def test_complete_when_all_soak_boundaries_pass():
    report = evaluate(evidence())
    assert report.action is ProductionSoakAction.COMPLETE
    assert report.safe and report.evidence_valid and report.soak_complete


@pytest.mark.parametrize("field", ["promotion_approved", "risk_approved", "capital_approved", "runtime_ready", "kill_switch_clear", "canary_completed"])
def test_upstream_safety_gate_aborts(field):
    assert evaluate(evidence(), **{field: False}).action is ProductionSoakAction.ABORT


def test_digest_tampering_aborts():
    report = evaluate(replace(evidence(), samples=1001))
    assert report.action is ProductionSoakAction.ABORT
    assert "evidence_digest_mismatch" in report.reasons


def test_identity_mismatch_aborts():
    item = evidence(strategy_version_id=uuid4())
    report = evaluate(item, expected_strategy_version_id=UUID("11111111-1111-1111-1111-111111111111"))
    assert report.action is ProductionSoakAction.ABORT


@pytest.mark.parametrize("field", ["samples", "reconciliation_failures", "missing_intervals"])
def test_negative_counts_rejected(field):
    with pytest.raises(ValueError):
        evidence(**{field: -1})


@pytest.mark.parametrize("field", ["cohort_percent", "observed_error_rate_percent", "observed_drawdown_percent", "observed_slippage_percent"])
def test_nonfinite_percentages_rejected(field):
    with pytest.raises(ValueError):
        evidence(**{field: "NaN"})


def test_naive_timestamp_rejected():
    with pytest.raises(ValueError):
        evidence(started_at=datetime(2026, 9, 1))


def test_inverted_time_window_rejected():
    with pytest.raises(ValueError):
        evidence(ended_at=START - timedelta(seconds=1))


def test_stale_evidence_aborts():
    report = evaluate(evidence(), now=START + timedelta(days=2))
    assert report.action is ProductionSoakAction.ABORT
    assert "evidence_stale" in report.reasons


def test_threshold_failure_aborts():
    report = evaluate(evidence(observed_error_rate_percent=Decimal("1.01")))
    assert report.action is ProductionSoakAction.ABORT
    assert "error_rate_exceeded" in report.reasons


def test_insufficient_evidence_holds():
    report = evaluate(evidence(samples=999))
    assert report.action is ProductionSoakAction.HOLD
    assert "insufficient_evidence_samples" in report.reasons


def test_short_soak_holds():
    ended_at = START + timedelta(hours=23)
    collected_at = ended_at + timedelta(minutes=1)
    item = evidence(ended_at=ended_at, collected_at=collected_at)
    report = evaluate(item, now=collected_at + timedelta(minutes=5))
    assert report.action is ProductionSoakAction.HOLD
    assert "insufficient_soak_duration" in report.reasons


def test_identical_evaluations_are_deterministic():
    item = evidence()
    assert evaluate(item) == evaluate(item)


def test_integration_is_read_only_and_never_widens_policy():
    integration = AutonomousProductionSoakIntegration()
    assert integration.policy.minimum_samples == 1000
    item = evidence()
    report = integration.evaluate(
        evidence=item, expected_strategy_version_id=item.strategy_version_id,
        expected_canary_run_id=item.canary_run_id, canary_completed=True,
        promotion_approved=True, risk_approved=True, capital_approved=True,
        runtime_ready=True, kill_switch_clear=True, now=NOW,
    )
    assert report.soak_complete and item == evidence()


def test_kill_switch_can_never_complete():
    report = evaluate(evidence(), kill_switch_clear=False)
    assert not report.soak_complete and not report.safe
