from decimal import Decimal

from packages.autonomy.learning import DriftAssessment, LearningAction
from packages.autonomy.strategy_evaluation import (
    AutonomousStrategyEvaluator,
    StrategyEvaluationAction,
    StrategyEvaluationStatus,
)


def assessment(action: LearningAction, score: str = "0.8", sample: int = 20) -> DriftAssessment:
    return DriftAssessment("s1", action, Decimal(score), (), sample)


def test_continue_is_accepted() -> None:
    report = AutonomousStrategyEvaluator().evaluate(assessment(LearningAction.CONTINUE))
    assert report.status is StrategyEvaluationStatus.ACCEPT
    assert report.action is StrategyEvaluationAction.CONTINUE


def test_review_is_quarantined() -> None:
    report = AutonomousStrategyEvaluator().evaluate(assessment(LearningAction.REVIEW))
    assert report.status is StrategyEvaluationStatus.REVIEW
    assert report.action is StrategyEvaluationAction.QUARANTINE


def test_retirement_candidate_is_rejected() -> None:
    report = AutonomousStrategyEvaluator().evaluate(assessment(LearningAction.RETIRE_CANDIDATE))
    assert report.status is StrategyEvaluationStatus.REJECT
    assert report.action is StrategyEvaluationAction.RETIRE_CANDIDATE


def test_small_sample_is_reviewed() -> None:
    report = AutonomousStrategyEvaluator().evaluate(assessment(LearningAction.CONTINUE, sample=19))
    assert report.status is StrategyEvaluationStatus.REVIEW


def test_low_score_is_rejected() -> None:
    report = AutonomousStrategyEvaluator().evaluate(assessment(LearningAction.CONTINUE, score="0.49"))
    assert report.status is StrategyEvaluationStatus.REJECT
    assert report.action is StrategyEvaluationAction.RETIRE_CANDIDATE


def test_empty_strategy_id_is_rejected() -> None:
    report = AutonomousStrategyEvaluator().evaluate(
        DriftAssessment("", LearningAction.CONTINUE, Decimal("0.8"), (), 20)
    )
    assert report is not None
