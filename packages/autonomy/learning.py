"""Deterministic strategy-performance learning and drift evaluation.

This module observes outcomes; it never mutates an active strategy version or
promotes a strategy on its own.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from statistics import mean


class LearningAction(str, Enum):
    CONTINUE = "continue"
    REVIEW = "review"
    RETIRE_CANDIDATE = "retire_candidate"


@dataclass(frozen=True, slots=True)
class StrategyPerformance:
    strategy_version_id: str
    trades: int
    realized_return: Decimal
    max_drawdown: Decimal
    win_rate: Decimal
    observed_at: float

    def __post_init__(self) -> None:
        if not self.strategy_version_id:
            raise ValueError("strategy_version_id is required")
        if self.trades < 0:
            raise ValueError("trades must be non-negative")
        if not 0 <= self.win_rate <= 1:
            raise ValueError("win_rate must be between 0 and 1")
        if self.max_drawdown < 0:
            raise ValueError("max_drawdown must be non-negative")
        if self.observed_at <= 0:
            raise ValueError("observed_at must be positive")


@dataclass(frozen=True, slots=True)
class DriftAssessment:
    strategy_version_id: str
    action: LearningAction
    score: Decimal
    reasons: tuple[str, ...]
    sample_size: int


@dataclass(frozen=True, slots=True)
class LearningPolicy:
    min_trades: int = 20
    max_drawdown: Decimal = Decimal("0.20")
    min_return: Decimal = Decimal("0")
    min_win_rate: Decimal = Decimal("0.40")
    review_score: Decimal = Decimal("0.50")
    retire_score: Decimal = Decimal("0.20")

    def __post_init__(self) -> None:
        if self.min_trades < 1:
            raise ValueError("min_trades must be positive")
        if not 0 < self.max_drawdown <= 1:
            raise ValueError("max_drawdown must be in (0, 1]")
        if not 0 <= self.min_win_rate <= 1:
            raise ValueError("min_win_rate must be between 0 and 1")
        if not 0 <= self.review_score <= 1 or not 0 <= self.retire_score <= 1:
            raise ValueError("score thresholds must be between 0 and 1")
        if self.retire_score >= self.review_score:
            raise ValueError("retire_score must be below review_score")


class StrategyLearningEngine:
    """Compare observed strategy outcomes with deterministic policy bounds."""

    def __init__(self, policy: LearningPolicy | None = None) -> None:
        self.policy = policy or LearningPolicy()

    def assess(self, observations: list[StrategyPerformance]) -> DriftAssessment:
        if not observations:
            raise ValueError("at least one observation is required")
        strategy_id = observations[-1].strategy_version_id
        if any(item.strategy_version_id != strategy_id for item in observations):
            raise ValueError("all observations must belong to one strategy version")

        sample = sum(item.trades for item in observations)
        if sample == 0:
            return DriftAssessment(strategy_id, LearningAction.REVIEW, Decimal("0"), ("no_trades",), 0)

        avg_return = Decimal(str(mean(float(item.realized_return) for item in observations)))
        avg_drawdown = Decimal(str(mean(float(item.max_drawdown) for item in observations)))
        avg_win_rate = Decimal(str(mean(float(item.win_rate) for item in observations)))
        score = Decimal("1")
        reasons: list[str] = []

        if avg_return < self.policy.min_return:
            score -= Decimal("0.35")
            reasons.append("return_below_floor")
        if avg_drawdown > self.policy.max_drawdown:
            score -= Decimal("0.35")
            reasons.append("drawdown_above_limit")
        if avg_win_rate < self.policy.min_win_rate:
            score -= Decimal("0.20")
            reasons.append("win_rate_below_floor")
        if sample < self.policy.min_trades:
            reasons.append("insufficient_sample")
            score = min(score, Decimal("0.50"))

        score = max(Decimal("0"), min(Decimal("1"), score))
        if score < self.policy.retire_score and sample >= self.policy.min_trades:
            action = LearningAction.RETIRE_CANDIDATE
        elif score < self.policy.review_score or "insufficient_sample" in reasons:
            action = LearningAction.REVIEW
        else:
            action = LearningAction.CONTINUE
        return DriftAssessment(strategy_id, action, score, tuple(reasons), sample)
