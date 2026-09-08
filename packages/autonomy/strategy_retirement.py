"""Deterministic, bounded strategy retirement automation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .strategy_evaluation import StrategyEvaluationAction, StrategyEvaluationReport, StrategyEvaluationStatus
from .strategy_lifecycle import StrategyLifecycleState


class StrategyRetirementAction(StrEnum):
    RETIRE = "retire"
    HOLD = "hold"
    BLOCK = "block"


@dataclass(frozen=True, slots=True)
class StrategyRetirementReport:
    strategy_version_id: str
    previous_state: StrategyLifecycleState
    action: StrategyRetirementAction
    safe: bool
    reasons: tuple[str, ...] = ()

    @property
    def should_retire(self) -> bool:
        return self.action is StrategyRetirementAction.RETIRE


class AutonomousStrategyRetirement:
    """Plan one deterministic retirement transition without mutating state."""

    def evaluate(
        self,
        *,
        strategy_version_id: str,
        current_state: StrategyLifecycleState,
        evaluation: StrategyEvaluationReport,
    ) -> StrategyRetirementReport:
        if not strategy_version_id.strip():
            raise ValueError("strategy_version_id is required")
        if evaluation.strategy_version_id != strategy_version_id:
            return StrategyRetirementReport(
                strategy_version_id,
                current_state,
                StrategyRetirementAction.BLOCK,
                False,
                ("strategy_identity_mismatch",),
            )

        if current_state is StrategyLifecycleState.RETIRED:
            return StrategyRetirementReport(
                strategy_version_id,
                current_state,
                StrategyRetirementAction.HOLD,
                True,
                ("already_retired",),
            )

        if (
            evaluation.status is StrategyEvaluationStatus.REJECT
            and evaluation.action is StrategyEvaluationAction.RETIRE_CANDIDATE
        ):
            return StrategyRetirementReport(
                strategy_version_id,
                current_state,
                StrategyRetirementAction.RETIRE,
                True,
                evaluation.reasons or ("evaluation_rejected_strategy",),
            )

        if evaluation.status is StrategyEvaluationStatus.REVIEW:
            return StrategyRetirementReport(
                strategy_version_id,
                current_state,
                StrategyRetirementAction.HOLD,
                True,
                evaluation.reasons or ("evaluation_requires_review",),
            )

        return StrategyRetirementReport(
            strategy_version_id,
            current_state,
            StrategyRetirementAction.HOLD,
            True,
            evaluation.reasons or ("retirement_not_authorized",),
        )
