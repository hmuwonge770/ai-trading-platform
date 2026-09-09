"""Integration boundary for controlled production expansion."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from .controlled_expansion import (
    ControlledExpansionPolicy,
    ExpansionReport,
    ExpansionRequest,
    evaluate_expansion,
)


@dataclass(frozen=True, slots=True)
class ControlledExpansionContext:
    """Immutable upstream gates; AX never mutates them."""

    canary_completed: bool
    soak_completed: bool
    promotion_approved: bool
    risk_approved: bool
    capital_approved: bool
    runtime_ready: bool
    kill_switch_clear: bool
    explicit_operator_approval: bool


class AutonomousControlledExpansionIntegration:
    """Compose upstream evidence into a bounded expansion recommendation."""

    def __init__(self, *, policy: ControlledExpansionPolicy | None = None) -> None:
        self._policy = policy

    @property
    def policy(self) -> ControlledExpansionPolicy:
        return self._policy or ControlledExpansionPolicy()

    def evaluate(
        self,
        *,
        strategy_version_id: UUID,
        context: ControlledExpansionContext,
        current_cohort_percent,
        requested_cohort_percent,
        soak_samples: int,
        observed_error_rate_percent,
        observed_drawdown_percent,
        observed_slippage_percent,
        reconciliation_failures: int,
    ) -> ExpansionReport:
        return evaluate_expansion(
            ExpansionRequest(
                strategy_version_id=strategy_version_id,
                current_cohort_percent=current_cohort_percent,
                requested_cohort_percent=requested_cohort_percent,
                soak_samples=soak_samples,
                observed_error_rate_percent=observed_error_rate_percent,
                observed_drawdown_percent=observed_drawdown_percent,
                observed_slippage_percent=observed_slippage_percent,
                reconciliation_failures=reconciliation_failures,
                canary_completed=context.canary_completed,
                soak_completed=context.soak_completed,
                promotion_approved=context.promotion_approved,
                risk_approved=context.risk_approved,
                capital_approved=context.capital_approved,
                runtime_ready=context.runtime_ready,
                kill_switch_clear=context.kill_switch_clear,
                explicit_operator_approval=context.explicit_operator_approval,
            ),
            policy=self.policy,
        )
