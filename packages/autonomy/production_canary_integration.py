"""Integration boundary for production-canary decisions.

The integration only composes already-approved gates. It does not activate the
runtime or mutate promotion, authorization, risk, capital, or kill-switch state.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from .production_canary import (
    AutonomousProductionCanaryGovernance,
    ProductionCanaryAction,
    ProductionCanaryPolicy,
    ProductionCanaryReport,
    ProductionCanaryRequest,
)


@dataclass(frozen=True, slots=True)
class ProductionCanaryGovernanceContext:
    """Immutable upstream approvals consumed by AQ."""

    promotion_approved: bool
    risk_approved: bool
    capital_approved: bool
    runtime_ready: bool
    kill_switch_clear: bool
    explicit_operator_approval: bool


class AutonomousProductionCanaryIntegration:
    """Require every upstream gate before a bounded canary may be planned."""

    def __init__(self, *, policy: ProductionCanaryPolicy | None = None) -> None:
        self._governance = AutonomousProductionCanaryGovernance(policy=policy)

    @property
    def policy(self) -> ProductionCanaryPolicy:
        return self._governance.policy

    def evaluate(
        self,
        *,
        strategy_version_id: UUID,
        context: ProductionCanaryGovernanceContext,
        requested_cohort_percent,
        evidence_samples: int,
        observed_error_rate_percent,
        reconciliation_failures: int,
        observed_drawdown_percent,
        observed_slippage_percent,
    ) -> ProductionCanaryReport:
        report = self._governance.evaluate(
            ProductionCanaryRequest(
                strategy_version_id=strategy_version_id,
                requested_cohort_percent=requested_cohort_percent,
                evidence_samples=evidence_samples,
                observed_error_rate_percent=observed_error_rate_percent,
                reconciliation_failures=reconciliation_failures,
                observed_drawdown_percent=observed_drawdown_percent,
                observed_slippage_percent=observed_slippage_percent,
                promotion_approved=context.promotion_approved,
                risk_approved=context.risk_approved,
                capital_approved=context.capital_approved,
                runtime_ready=context.runtime_ready,
                kill_switch_clear=context.kill_switch_clear,
                explicit_operator_approval=context.explicit_operator_approval,
            )
        )
        if report.action is ProductionCanaryAction.START and not context.kill_switch_clear:
            raise AssertionError("canary cannot start while deployment kill switch is active")
        return report
