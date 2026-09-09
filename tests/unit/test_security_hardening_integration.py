from packages.autonomy.security_hardening import SecurityObservation, SecurityStatus
from packages.autonomy.security_hardening_integration import (
    AutonomousSecurityHardeningIntegration,
    SecurityGovernanceContext,
)


def test_integration_requires_strategy_identity():
    context = SecurityGovernanceContext("", "v1", SecurityObservation(True, True, True, True, True, True))
    report = AutonomousSecurityHardeningIntegration().assess(context)
    assert report.status is SecurityStatus.BLOCKED
    assert report.reasons == ("strategy_identity_missing",)


def test_integration_is_read_only_and_returns_secure_assessment():
    observation = SecurityObservation(True, True, True, True, True, True)
    context = SecurityGovernanceContext("strategy-a", "v1", observation)
    report = AutonomousSecurityHardeningIntegration().assess(context)
    assert report.status is SecurityStatus.SECURE
    assert context.observation is observation
