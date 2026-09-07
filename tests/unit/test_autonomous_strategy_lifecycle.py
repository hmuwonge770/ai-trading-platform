from decimal import Decimal

from packages.autonomy.learning import DriftAssessment, LearningAction
from packages.autonomy.strategy_lifecycle import (
    AutonomousStrategyLifecycle,
    StrategyLifecycleAction,
    StrategyLifecycleState,
)


def assessment(strategy: str, action: LearningAction, sample: int = 20) -> DriftAssessment:
    return DriftAssessment(strategy, action, Decimal("0.8"), (), sample)


def test_active_strategy_is_quarantined_on_review() -> None:
    report = AutonomousStrategyLifecycle().evaluate(
        strategy_version_id="s1",
        current_state=StrategyLifecycleState.ACTIVE,
        assessment=assessment("s1", LearningAction.REVIEW),
    )
    assert report.state == StrategyLifecycleState.QUARANTINED
    assert report.action == StrategyLifecycleAction.QUARANTINE


def test_retirement_candidate_is_retired() -> None:
    report = AutonomousStrategyLifecycle().evaluate(
        strategy_version_id="s1",
        current_state=StrategyLifecycleState.ACTIVE,
        assessment=assessment("s1", LearningAction.RETIRE_CANDIDATE),
    )
    assert report.state == StrategyLifecycleState.RETIRED
    assert report.action == StrategyLifecycleAction.RETIRE


def test_candidate_activation_is_blocked_by_default() -> None:
    report = AutonomousStrategyLifecycle().evaluate(
        strategy_version_id="s1",
        current_state=StrategyLifecycleState.CANDIDATE,
        assessment=assessment("s1", LearningAction.CONTINUE),
    )
    assert report.state == StrategyLifecycleState.CANDIDATE
    assert report.action == StrategyLifecycleAction.BLOCK


def test_quarantined_strategy_cannot_self_reactivate() -> None:
    report = AutonomousStrategyLifecycle().evaluate(
        strategy_version_id="s1",
        current_state=StrategyLifecycleState.QUARANTINED,
        assessment=assessment("s1", LearningAction.CONTINUE),
    )
    assert report.state == StrategyLifecycleState.QUARANTINED
    assert report.action == StrategyLifecycleAction.BLOCK


def test_identity_mismatch_fails_closed() -> None:
    report = AutonomousStrategyLifecycle().evaluate(
        strategy_version_id="s1",
        current_state=StrategyLifecycleState.ACTIVE,
        assessment=assessment("s2", LearningAction.CONTINUE),
    )
    assert not report.safe
    assert report.action == StrategyLifecycleAction.BLOCK


def test_retired_strategy_is_immutable() -> None:
    report = AutonomousStrategyLifecycle().evaluate(
        strategy_version_id="s1",
        current_state=StrategyLifecycleState.RETIRED,
        assessment=assessment("s1", LearningAction.CONTINUE),
    )
    assert report.state == StrategyLifecycleState.RETIRED
    assert report.action == StrategyLifecycleAction.NOOP
