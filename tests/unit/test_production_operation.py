from decimal import Decimal

import pytest

from packages.autonomy.production_operation import (
    ProductionOperationAction,
    ProductionOperationObservation,
    ProductionOperationPolicy,
    assess_production_operation,
)


def ready() -> ProductionOperationObservation:
    return ProductionOperationObservation(
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


def test_ready_operation_is_deterministically_allowed() -> None:
    observation = ready()
    first = assess_production_operation(observation)
    second = assess_production_operation(observation)
    assert first == second
    assert first.action is ProductionOperationAction.OPERATE
    assert first.reasons == ()


def test_kill_switch_is_hard_halt() -> None:
    observation = ready()
    observation = ProductionOperationObservation(
        **{**{field: getattr(observation, field) for field in observation.__dataclass_fields__}, "deployment_kill_switch_active": True}
    )
    assessment = assess_production_operation(observation)
    assert assessment.action is ProductionOperationAction.HALT
    assert "deployment_kill_switch_active" in assessment.reasons


@pytest.mark.parametrize(
    ("field", "reason"),
    [
        ("live_authorized", "live_authorization_missing"),
        ("runtime_enabled", "runtime_not_enabled"),
        ("operator_shutdown_available", "operator_shutdown_unavailable"),
        ("capital_approved", "capital_governance_not_approved"),
        ("risk_approved", "risk_governance_not_approved"),
        ("readiness_approved", "production_readiness_not_approved"),
        ("lifecycle_validation_passed", "lifecycle_validation_not_passed"),
        ("security_secure", "security_not_secure"),
        ("incident_recovery_verified", "incident_recovery_not_verified"),
    ],
)
def test_missing_required_gate_halts(field: str, reason: str) -> None:
    observation = ready()
    values = {name: getattr(observation, name) for name in observation.__dataclass_fields__}
    values[field] = False
    assessment = assess_production_operation(ProductionOperationObservation(**values))
    assert assessment.action is ProductionOperationAction.HALT
    assert reason in assessment.reasons


def test_strategy_identity_is_required() -> None:
    observation = ready()
    values = {name: getattr(observation, name) for name in observation.__dataclass_fields__}
    values["strategy_fingerprint"] = None
    assessment = assess_production_operation(ProductionOperationObservation(**values))
    assert assessment.action is ProductionOperationAction.HALT
    assert "strategy_identity_missing" in assessment.reasons


def test_nonfinite_metric_fails_closed() -> None:
    observation = ready()
    values = {name: getattr(observation, name) for name in observation.__dataclass_fields__}
    values["error_rate_percent"] = Decimal("NaN")
    assessment = assess_production_operation(ProductionOperationObservation(**values))
    assert assessment.action is ProductionOperationAction.HALT
    assert "invalid_error_rate_percent" in assessment.reasons


def test_policy_cannot_widen_hard_ceilings() -> None:
    with pytest.raises(ValueError):
        ProductionOperationPolicy(maximum_daily_loss_percent=Decimal("2.01"))
    with pytest.raises(ValueError):
        ProductionOperationPolicy(maximum_cohort_percent=Decimal("5.01"))


def test_reconciliation_failure_halts() -> None:
    observation = ready()
    values = {name: getattr(observation, name) for name in observation.__dataclass_fields__}
    values["reconciliation_failures"] = 1
    assessment = assess_production_operation(ProductionOperationObservation(**values))
    assert assessment.action is ProductionOperationAction.HALT
    assert "reconciliation_failures_exceeded" in assessment.reasons
