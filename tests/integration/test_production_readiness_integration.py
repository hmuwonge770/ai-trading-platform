from packages.autonomy.production_readiness import ProductionReadinessObservation, ReadinessStatus
from packages.autonomy.production_readiness_integration import (
    AutonomousProductionReadinessIntegration,
    ProductionReadinessGovernanceContext,
)


def observation():
    return ProductionReadinessObservation(
        soak_complete=True,
        failure_testing_complete=True,
        slo_healthy=True,
        security_secure=True,
        incident_recovery_verified=True,
        operator_approved=True,
        runtime_preflight_passed=True,
        strategy_id="strategy-1",
        strategy_version="v1",
    )


def test_integration_preserves_ready_result():
    result = AutonomousProductionReadinessIntegration.assess(
        ProductionReadinessGovernanceContext(observation())
    )
    assert result.status is ReadinessStatus.READY


def test_integration_blocks_failed_preflight():
    base = observation()
    failed = ProductionReadinessObservation(
        **{**base.__dict__, "runtime_preflight_passed": False}
    )
    result = AutonomousProductionReadinessIntegration.assess(
        ProductionReadinessGovernanceContext(failed)
    )
    assert result.status is ReadinessStatus.BLOCKED
    assert result.reasons == ("runtime_preflight_failed",)
