from packages.autonomy.autonomous_lifecycle_validation import LifecycleValidationAction
from packages.autonomy.autonomous_lifecycle_validation_integration import (
    AutonomousLifecycleValidationIntegration,
    LifecycleValidationContext,
)


def context(**overrides):
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
    return LifecycleValidationContext(**values)


def test_integration_passes_complete_lifecycle():
    assessment = AutonomousLifecycleValidationIntegration().assess(context())
    assert assessment.action is LifecycleValidationAction.PASS


def test_integration_cannot_bypass_capital_gate():
    assessment = AutonomousLifecycleValidationIntegration().assess(context(capital_approved=False))
    assert assessment.action is LifecycleValidationAction.BLOCK


def test_integration_cannot_bypass_runtime_gate():
    assessment = AutonomousLifecycleValidationIntegration().assess(context(runtime_ready=False))
    assert assessment.action is LifecycleValidationAction.BLOCK
