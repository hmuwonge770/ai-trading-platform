from packages.autonomy.autonomous_lifecycle_validation import (
    LifecycleValidationAction,
    LifecycleValidationObservation,
    validate_lifecycle,
)


def complete_observation(**overrides):
    values = dict(
        strategy_identity_verified=True,
        promotion_approved=True,
        canary_completed=True,
        soak_completed=True,
        expansion_validated=True,
        incident_recovery_verified=True,
        retirement_validated=True,
        risk_approved=True,
        capital_approved=True,
        runtime_ready=True,
        kill_switch_clear=True,
        operator_approval=True,
    )
    values.update(overrides)
    return LifecycleValidationObservation(**values)


def test_complete_lifecycle_passes():
    assessment = validate_lifecycle(complete_observation())
    assert assessment.action is LifecycleValidationAction.PASS
    assert assessment.safe
    assert assessment.reasons == ()


def test_identity_failure_blocks():
    assessment = validate_lifecycle(complete_observation(strategy_identity_verified=False))
    assert assessment.action is LifecycleValidationAction.BLOCK
    assert not assessment.safe
    assert assessment.reasons[0] == "strategy_identity_mismatch"


def test_kill_switch_blocks():
    assessment = validate_lifecycle(complete_observation(kill_switch_clear=False))
    assert assessment.action is LifecycleValidationAction.BLOCK
    assert not assessment.safe


def test_missing_operator_approval_holds():
    assessment = validate_lifecycle(complete_observation(operator_approval=False))
    assert assessment.action is LifecycleValidationAction.HOLD
    assert assessment.safe
    assert assessment.reasons == ("operator_approval_missing",)


def test_missing_expansion_evidence_holds():
    assessment = validate_lifecycle(complete_observation(expansion_validated=False))
    assert assessment.action is LifecycleValidationAction.HOLD
    assert assessment.safe
    assert assessment.reasons == ("expansion_not_validated",)


def test_evaluation_is_deterministic():
    observation = complete_observation(operator_approval=False)
    assert validate_lifecycle(observation) == validate_lifecycle(observation)
