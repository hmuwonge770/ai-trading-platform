"""Fail-closed strategy lifecycle automation driven by deterministic evidence."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .learning import DriftAssessment, LearningAction


class StrategyLifecycleState(StrEnum):
    DRAFT = "draft"
    CANDIDATE = "candidate"
    ACTIVE = "active"
    QUARANTINED = "quarantined"
    RETIRED = "retired"


class StrategyLifecycleAction(StrEnum):
    NOOP = "noop"
    ACTIVATE = "activate"
    QUARANTINE = "quarantine"
    RETIRE = "retire"
    BLOCK = "block"


@dataclass(frozen=True, slots=True)
class StrategyLifecyclePolicy:
    """Bound lifecycle transitions; never grants live execution authority."""

    allow_candidate_activation: bool = False
    require_min_sample_for_activation: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.allow_candidate_activation, bool):
            raise ValueError("allow_candidate_activation must be boolean")
        if not isinstance(self.require_min_sample_for_activation, bool):
            raise ValueError("require_min_sample_for_activation must be boolean")


@dataclass(frozen=True, slots=True)
class StrategyLifecycleReport:
    strategy_version_id: str
    previous_state: StrategyLifecycleState
    state: StrategyLifecycleState
    action: StrategyLifecycleAction
    safe: bool
    reasons: tuple[str, ...] = ()


class AutonomousStrategyLifecycle:
    """Apply deterministic, bounded lifecycle transitions to one strategy."""

    def __init__(self, policy: StrategyLifecyclePolicy | None = None) -> None:
        self.policy = policy or StrategyLifecyclePolicy()

    def evaluate(
        self,
        *,
        strategy_version_id: str,
        current_state: StrategyLifecycleState,
        assessment: DriftAssessment,
    ) -> StrategyLifecycleReport:
        if not strategy_version_id.strip():
            raise ValueError("strategy_version_id is required")
        if assessment.strategy_version_id != strategy_version_id:
            return StrategyLifecycleReport(
                strategy_version_id, current_state, current_state,
                StrategyLifecycleAction.BLOCK, False, ("strategy_identity_mismatch",)
            )

        if current_state == StrategyLifecycleState.RETIRED:
            return StrategyLifecycleReport(strategy_version_id, current_state, current_state, StrategyLifecycleAction.NOOP, True)

        if assessment.action == LearningAction.RETIRE_CANDIDATE:
            return StrategyLifecycleReport(
                strategy_version_id, current_state, StrategyLifecycleState.RETIRED,
                StrategyLifecycleAction.RETIRE, True, ("learning_retirement_candidate",)
            )

        if assessment.action == LearningAction.REVIEW:
            target = StrategyLifecycleState.QUARANTINED if current_state == StrategyLifecycleState.ACTIVE else current_state
            action = StrategyLifecycleAction.QUARANTINE if target != current_state else StrategyLifecycleAction.NOOP
            return StrategyLifecycleReport(strategy_version_id, current_state, target, action, True, ("learning_review_required",))

        if current_state == StrategyLifecycleState.CANDIDATE:
            if not self.policy.allow_candidate_activation:
                return StrategyLifecycleReport(
                    strategy_version_id, current_state, current_state,
                    StrategyLifecycleAction.BLOCK, True, ("candidate_activation_requires_governance",)
                )
            if self.policy.require_min_sample_for_activation and assessment.sample_size <= 0:
                return StrategyLifecycleReport(
                    strategy_version_id, current_state, current_state,
                    StrategyLifecycleAction.BLOCK, True, ("activation_requires_observations",)
                )
            return StrategyLifecycleReport(
                strategy_version_id, current_state, StrategyLifecycleState.ACTIVE,
                StrategyLifecycleAction.ACTIVATE, True
            )

        if current_state == StrategyLifecycleState.QUARANTINED and assessment.action == LearningAction.CONTINUE:
            return StrategyLifecycleReport(
                strategy_version_id, current_state, current_state,
                StrategyLifecycleAction.BLOCK, True, ("quarantined_requires_explicit_review",)
            )

        return StrategyLifecycleReport(strategy_version_id, current_state, current_state, StrategyLifecycleAction.NOOP, True)
