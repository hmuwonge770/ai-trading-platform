from decimal import Decimal
from uuid import UUID

from packages.autonomy.production_canary import ProductionCanaryAction
from packages.autonomy.production_canary_integration import (
    AutonomousProductionCanaryIntegration,
    ProductionCanaryGovernanceContext,
)


STRATEGY_ID = UUID("12345678-1234-5678-1234-567812345678")


def evaluate(**context_overrides):
    values = dict(
        promotion_approved=True,
        risk_approved=True,
        capital_approved=True,
        runtime_ready=True,
        kill_switch_clear=True,
        explicit_operator_approval=True,
    )
    values.update(context_overrides)
    return AutonomousProductionCanaryIntegration().evaluate(
        strategy_version_id=STRATEGY_ID,
        context=ProductionCanaryGovernanceContext(**values),
        requested_cohort_percent=Decimal("100"),
        evidence_samples=100,
        observed_error_rate_percent=Decimal("0"),
        reconciliation_failures=0,
        observed_drawdown_percent=Decimal("0"),
        observed_slippage_percent=Decimal("0"),
    )


def test_all_upstream_gates_are_required():
    for gate in ("promotion_approved", "risk_approved", "capital_approved", "runtime_ready", "kill_switch_clear"):
        report = evaluate(**{gate: False})
        assert report.action is ProductionCanaryAction.ABORT


def test_operator_approval_without_other_failures_holds():
    report = evaluate(explicit_operator_approval=False)
    assert report.action is ProductionCanaryAction.HOLD


def test_integration_does_not_widen_policy():
    integration = AutonomousProductionCanaryIntegration()
    before = integration.policy
    evaluate()
    assert integration.policy == before
