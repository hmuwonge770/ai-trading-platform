from decimal import Decimal
from uuid import UUID

from packages.autonomy.controlled_expansion import ExpansionAction
from packages.autonomy.controlled_expansion_integration import (
    AutonomousControlledExpansionIntegration,
    ControlledExpansionContext,
)


STRATEGY = UUID("12345678-1234-5678-1234-567812345678")


def context(**overrides):
    values = dict(
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
    return ControlledExpansionContext(**values)


def evaluate(ctx=None):
    return AutonomousControlledExpansionIntegration().evaluate(
        strategy_version_id=STRATEGY,
        context=ctx or context(),
        current_cohort_percent=Decimal("1"),
        requested_cohort_percent=Decimal("2"),
        soak_samples=1000,
        observed_error_rate_percent=Decimal("0.5"),
        observed_drawdown_percent=Decimal("1"),
        observed_slippage_percent=Decimal("0.5"),
        reconciliation_failures=0,
    )


def test_integration_allows_only_bounded_recommendation():
    report = evaluate()
    assert report.action is ExpansionAction.EXPAND
    assert report.approved_delta_percent == Decimal("1")


def test_kill_switch_blocks_expansion():
    report = evaluate(context(kill_switch_clear=False))
    assert report.action is ExpansionAction.ABORT
    assert "deployment_kill_switch_active" in report.reasons


def test_runtime_not_ready_blocks_expansion():
    report = evaluate(context(runtime_ready=False))
    assert report.action is ExpansionAction.ABORT


def test_capital_gate_is_never_bypassed():
    report = evaluate(context(capital_approved=False))
    assert report.action is ExpansionAction.ABORT
    assert "capital_governance_not_approved" in report.reasons
