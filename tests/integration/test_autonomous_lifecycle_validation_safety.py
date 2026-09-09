from packages.autonomy.autonomous_lifecycle_validation import LifecycleValidationAction
from packages.autonomy.autonomous_lifecycle_validation_integration import AutonomousLifecycleValidationIntegration, LifecycleValidationContext


def valid(**changes):
    values = {field: True for field in LifecycleValidationContext.__dataclass_fields__}
    values.update(changes)
    return LifecycleValidationContext(**values)


def test_unknown_or_unsafe_runtime_state_cannot_pass():
    result = AutonomousLifecycleValidationIntegration().assess(valid(runtime_ready=False))
    assert result.action is LifecycleValidationAction.BLOCK
    assert not result.safe


def test_security_boundary_cannot_be_bypassed_by_other_gates():
    result = AutonomousLifecycleValidationIntegration().assess(valid(strategy_identity_verified=False))
    assert result.action is LifecycleValidationAction.BLOCK
    assert not result.safe


def test_kill_switch_remains_hard_boundary():
    result = AutonomousLifecycleValidationIntegration().assess(valid(kill_switch_clear=False))
    assert result.action is LifecycleValidationAction.BLOCK
    assert not result.safe
