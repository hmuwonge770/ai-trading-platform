from decimal import Decimal

import pytest

from packages.autonomy.learning import (
    DriftAssessment,
    LearningAction,
    LearningPolicy,
    StrategyLearningEngine,
    StrategyPerformance,
)


def performance(return_value: str, drawdown: str, win_rate: str, trades: int = 20) -> StrategyPerformance:
    return StrategyPerformance(
        strategy_version_id="v1",
        trades=trades,
        realized_return=Decimal(return_value),
        max_drawdown=Decimal(drawdown),
        win_rate=Decimal(win_rate),
        observed_at=1_700_000_000,
    )


def test_healthy_strategy_continues() -> None:
    result = StrategyLearningEngine().assess([performance("0.05", "0.08", "0.55")])
    assert isinstance(result, DriftAssessment)
    assert result.action is LearningAction.CONTINUE
    assert result.score == Decimal("1")


def test_drift_requests_review() -> None:
    result = StrategyLearningEngine().assess([performance("-0.01", "0.10", "0.35")])
    assert result.action is LearningAction.REVIEW
    assert "return_below_floor" in result.reasons
    assert "win_rate_below_floor" in result.reasons


def test_severe_drift_marks_retirement_candidate() -> None:
    result = StrategyLearningEngine().assess([performance("-0.20", "0.40", "0.20")])
    assert result.action is LearningAction.RETIRE_CANDIDATE
    assert result.score == Decimal("0.10")


def test_insufficient_sample_fails_closed_to_review() -> None:
    result = StrategyLearningEngine().assess([performance("0.05", "0.08", "0.55", trades=3)])
    assert result.action is LearningAction.REVIEW
    assert "insufficient_sample" in result.reasons


def test_mixed_strategy_versions_are_rejected() -> None:
    first = performance("0.05", "0.08", "0.55")
    second = StrategyPerformance("v2", 20, Decimal("0.05"), Decimal("0.08"), Decimal("0.55"), 1_700_000_001)
    with pytest.raises(ValueError, match="one strategy version"):
        StrategyLearningEngine().assess([first, second])


def test_policy_thresholds_are_ordered() -> None:
    with pytest.raises(ValueError, match="retire_score"):
        LearningPolicy(review_score=Decimal("0.20"), retire_score=Decimal("0.20"))
