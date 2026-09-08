"""Integration boundary for production-soak evidence governance."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from .production_soak import ProductionSoakEvidence, ProductionSoakPolicy
from .production_soak_governance import AutonomousProductionSoakGovernance, ProductionSoakReport


class AutonomousProductionSoakIntegration:
    """Compose AQ completion and upstream approvals without mutating state."""

    def __init__(self, *, policy: ProductionSoakPolicy | None = None) -> None:
        self._governance = AutonomousProductionSoakGovernance(policy=policy)

    @property
    def policy(self) -> ProductionSoakPolicy:
        return self._governance.policy

    def evaluate(
        self,
        *,
        evidence: ProductionSoakEvidence,
        expected_strategy_version_id: UUID,
        expected_canary_run_id: UUID,
        canary_completed: bool,
        promotion_approved: bool,
        risk_approved: bool,
        capital_approved: bool,
        runtime_ready: bool,
        kill_switch_clear: bool,
        now: datetime,
    ) -> ProductionSoakReport:
        return self._governance.evaluate(
            evidence,
            expected_strategy_version_id=expected_strategy_version_id,
            expected_canary_run_id=expected_canary_run_id,
            canary_completed=canary_completed,
            promotion_approved=promotion_approved,
            risk_approved=risk_approved,
            capital_approved=capital_approved,
            runtime_ready=runtime_ready,
            kill_switch_clear=kill_switch_clear,
            now=now,
        )
