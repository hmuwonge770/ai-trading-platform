"""Deterministic strategy evaluation from existing learning evidence."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from .learning import DriftAssessment, LearningAction


class StrategyEvaluationStatus(StrEnum):
    ACCEPT = "accept"
    REVIEW = "review"
    REJECT = "reject"


class StrategyEvaluationAction(StrEnum):
    CONTINUE = "continue"
    QUARANTINE = "quarantine"
    RETIRE_CANDIDATE = "retire_candidate"


@dataclass(frozen=True, slots=True)
class StrategyEvaluationPolicy:
    """Bound evaluation outcomes without granting execution authority."""

    min_score: Decimal = Decimal("0.50")
    min_sample_size: int = 20

    def __post_init__(self) -> None:
        if not 0 <= self.min_score <= 1:
            raise ValueError("min_score must be between 0 and 1")
        if self.min_sample_size < 1:
            raise ValueError("min_sample_size must be positive")


@dataclass(frozen=True, slots=True)
class StrategyEvaluationReport:
    strategy_version_id: str
    status: StrategyEvaluationStatus
    action: StrategyEvaluationAction
    score: Decimal
    sample_size: int
    reasons: tuple[str, ...] = ()

    @property
    def accepted(self) -> bool:
        return self.status is StrategyEvaluationStatus.ACCEPT


class AutonomousStrategyEvaluator:
    """Evaluate one strategy using immutable deterministic learning evidence."""

    def __init__(self, policy: StrategyEvaluationPolicy | None = None) -> None:
        self.policy = policy or StrategyEvaluationPolicy()

    def evaluate(self, assessment: DriftAssessment) -> StrategyEvaluationReport:
        if not assessment.strategy_version_id.strip():
            raise ValueError("strategy_version_id is required")
        reasons = list(assessment.reasons)
        if assessment.action is LearningAction.RETIRE_CANDIDATE:
            return StrategyEvaluationReport(
                assessment.strategy_version_id,
                StrategyEvaluationStatus.REJECT,
                StrategyEvaluationAction.RETIRE_CANDIDATE,
                assessment.score,
                assessment.sample_size,
                tuple(reasons) or ("retirement_candidate",),
            )
        if assessment.action is LearningAction.REVIEW:
            return StrategyEvaluationReport(
                assessment.strategy_version_id,
                StrategyEvaluationStatus.REVIEW,
                StrategyEvaluationAction.QUARANTINE,
                assessment.score,
                assessment.sample_size,
                tuple(reasons) or ("review_required",),
            )
        if assessment.sample_size < self.policy.min_sample_size:
            reasons.append("insufficient_evaluation_sample")
            return StrategyEvaluationReport(
                assessment.strategy_version_id,
                StrategyEvaluationStatus.REVIEW,
                StrategyEvaluationAction.QUARANTINE,
                assessment.score,
                assessment.sample_size,
                tuple(reasons),
            )
        if assessment.score < self.policy.min_score:
            reasons.append("score_below_evaluation_floor")
            return StrategyEvaluationReport(
                assessment.strategy_version_id,
                StrategyEvaluationStatus.REJECT,
                StrategyEvaluationAction.RETIRE_CANDIDATE,
                assessment.score,
                assessment.sample_size,
                tuple(reasons),
            )
        return StrategyEvaluationReport(
            assessment.strategy_version_id,
            StrategyEvaluationStatus.ACCEPT,
            StrategyEvaluationAction.CONTINUE,
            assessment.score,
            assessment.sample_size,
            tuple(reasons),
        )
