"""Integration boundary for AU security governance."""
from dataclasses import dataclass

from .security_hardening import (
    SecurityAssessment,
    SecurityHardeningPolicy,
    SecurityObservation,
    assess_security,
)


@dataclass(frozen=True, slots=True)
class SecurityGovernanceContext:
    strategy_id: str
    strategy_version: str
    observation: SecurityObservation


class AutonomousSecurityHardeningIntegration:
    """Composes security evidence without mutating runtime or execution state."""

    def __init__(self, policy: SecurityHardeningPolicy | None = None) -> None:
        self._policy = policy or SecurityHardeningPolicy()

    def assess(self, context: SecurityGovernanceContext) -> SecurityAssessment:
        if not context.strategy_id or not context.strategy_version:
            return SecurityAssessment(status="blocked", reasons=("strategy_identity_missing",))
        return assess_security(self._policy, context.observation)
