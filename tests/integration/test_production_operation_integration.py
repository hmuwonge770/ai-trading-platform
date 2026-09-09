from dataclasses import replace
from decimal import Decimal

from packages.autonomy.production_operation import ProductionOperationAction
from packages.autonomy.production_operation_integration import (
    AutonomousProductionOperationIntegration,
    ProductionOperationContext,
)


def context() -> ProductionOperationContext:
    return ProductionOperationContext(
        strategy_version_id="strategy-v1",
        strategy_fingerprint="fingerprint-1",
        live_authorized=True,
        runtime_enabled=True,
        operator_shutdown_available=True,
        deployment_kill_switch_active=False,
        capital_approved=True,
        risk_approved=True,
        readiness_approved=True,
        lifecycle_validation_passed=True,
        canary_completed=True,
        soak_completed=True,
        failure_testing_passed=True,
        security_secure=True,
        incident_recovery_verified=True,
        reconciliation_failures=0,
        daily_loss_percent=Decimal("0"),
        drawdown_percent=Decimal("0"),
        error_rate_percent=Decimal("0"),
        slippage_percent=Decimal("0"),
    )


def test_integration_is_control_plane_only_and_deterministic() -> None:
    integration = AutonomousProductionOperationIntegration()
    first = integration.assess(context())
    second = integration.assess(context())
    assert first == second
    assert first.action is ProductionOperationAction.OPERATE


def test_integration_halts_on_kill_switch() -> None:
    integration = AutonomousProductionOperationIntegration()
    assessment = integration.assess(
        replace(context(), deployment_kill_switch_active=True)
    )
    assert assessment.action is ProductionOperationAction.HALT
    assert "deployment_kill_switch_active" in assessment.reasons
