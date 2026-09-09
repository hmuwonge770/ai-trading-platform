"""Governance boundary for end-to-end failure assessments."""
from dataclasses import dataclass
from .end_to_end_failure_testing import FailureAssessment, FailureInjection, FailureResponse, assess_failure


@dataclass(frozen=True, slots=True)
class FailureGovernanceContext:
    strategy_id: str
    strategy_version: str
    failure: FailureInjection


class AutonomousEndToEndFailureGovernance:
    """Control-plane only; produces bounded responses without executing them."""

    def assess(self, context: FailureGovernanceContext) -> FailureAssessment:
        if context.failure.strategy_id != context.strategy_id or context.failure.strategy_version != context.strategy_version:
            return FailureAssessment(context.failure.failure, FailureResponse.HALT, False, ("strategy_identity_mismatch",))
        return assess_failure(context.failure)
