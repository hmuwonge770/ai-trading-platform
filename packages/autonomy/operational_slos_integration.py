"""Composition boundary for operational SLO evidence."""
from dataclasses import dataclass
from .operational_slos import OperationalObservation, OperationalSLOPolicy
from .operational_slos_governance import AutonomousOperationalSLOGovernance, OperationalSLOReport


@dataclass(frozen=True, slots=True)
class OperationalGovernanceContext:
    kill_switch_clear: bool
    runtime_enabled: bool
    authorization_valid: bool


class AutonomousOperationalSLOIntegration:
    """Combines operational evidence with hard safety gates, read-only."""

    def __init__(self, policy: OperationalSLOPolicy | None = None) -> None:
        self._governance = AutonomousOperationalSLOGovernance(policy)

    def evaluate(self, observation: OperationalObservation, context: OperationalGovernanceContext) -> OperationalSLOReport:
        report = self._governance.evaluate(observation)
        reasons = list(report.reasons)
        if not context.kill_switch_clear:
            reasons.append("kill_switch_active")
        if not context.runtime_enabled:
            reasons.append("runtime_not_enabled")
        if not context.authorization_valid:
            reasons.append("authorization_invalid")
        if reasons != list(report.reasons):
            from dataclasses import replace
            from .operational_slos import SLOStatus
            status = SLOStatus.BLOCKED if any(x in reasons for x in ("kill_switch_active", "authorization_invalid")) else report.status
            return replace(report, status=status, reasons=tuple(reasons))
        return report
