from packages.autonomy.production_readiness import (
    ProductionReadinessObservation,
    ProductionReadinessPolicy,
    ReadinessStatus,
    assess_production_readiness,
)


def complete_observation(**overrides):
    values = dict(
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
    values.update(overrides)
    return ProductionReadinessObservation(**values)


def test_complete_evidence_is_ready():
    result = assess_production_readiness(complete_observation())
    assert result.status is ReadinessStatus.READY
    assert result.reasons == ()


def test_missing_strategy_identity_blocks():
    result = assess_production_readiness(complete_observation(strategy_id=""))
    assert result.status is ReadinessStatus.BLOCKED
    assert result.reasons == ("strategy_identity_missing",)


def test_all_required_failures_are_reported_deterministically():
    result = assess_production_readiness(
        complete_observation(
            soak_complete=False,
            failure_testing_complete=False,
            slo_healthy=False,
            security_secure=False,
            incident_recovery_verified=False,
            operator_approved=False,
            runtime_preflight_passed=False,
        )
    )
    assert result.status is ReadinessStatus.BLOCKED
    assert result.reasons == (
        "soak_evidence_missing",
        "failure_testing_missing",
        "slo_evidence_not_healthy",
        "security_evidence_not_secure",
        "incident_recovery_not_verified",
        "operator_approval_missing",
        "runtime_preflight_failed",
    )


def test_optional_evidence_can_be_disabled_but_identity_remains_required():
    policy = ProductionReadinessPolicy(
        require_soak_evidence=False,
        require_failure_evidence=False,
        require_slo_evidence=False,
        require_security_evidence=False,
        require_incident_recovery_evidence=False,
        require_operator_approval=False,
        require_runtime_preflight=False,
    )
    result = assess_production_readiness(
        complete_observation(soak_complete=False), policy
    )
    assert result.status is ReadinessStatus.READY


def test_operator_approval_is_independently_enforced():
    result = assess_production_readiness(complete_observation(operator_approved=False))
    assert result.status is ReadinessStatus.BLOCKED
    assert result.reasons == ("operator_approval_missing",)
