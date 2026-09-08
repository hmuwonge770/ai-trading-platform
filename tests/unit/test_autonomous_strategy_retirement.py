from decimal import Decimal

import pytest

from packages.autonomy.strategy_evaluation import (
    StrategyEvaluationAction,
    StrategyEvaluationReport,
    StrategyEvaluationStatus,
)
from packages.autonomy.strategy_lifecycle import StrategyLifecycleState
from packages.autonomy.strategy_retirement import (
    AutonomousStrategyRetirement,
    StrategyRetirementAction,
)


def evaluation(
    strategy_id: str = "s1",
    status: StrategyEvaluationStatus = StrategyEvaluationStatus.REJECT,
    action: StrategyEvaluationAction = StrategyEvaluationAction.RETIRE_CANDIDATE,
    reasons: tuple[str, ...] = ("score_below_evaluation_floor",),
) -> StrategyEvaluationReport:
    return StrategyEvaluationReport(strategy_id, status, action, Decimal("0.4"), 20, reasons)


def test_rejected_retirement_candidate_produces_retire() -> None:
    report = AutonomousStrategyRetirement().evaluate(
        strategy_version_id="s1",
        current_state=StrategyLifecycleState.ACTIVE,
        evaluation=evaluation(),
    )
    assert report.action is StrategyRetirementAction.RETIRE
    assert report.should_retire
    assert report.safe


def test_candidate_can_be_marked_for_retirement_without_activation() -> None:
    report = AutonomousStrategyRetirement().evaluate(
        strategy_version_id="s1",
        current_state=StrategyLifecycleState.CANDIDATE,
        evaluation=evaluation(),
    )
    assert report.action is StrategyRetirementAction.RETIRE


def test_already_retired_is_idempotent() -> None:
    report = AutonomousStrategyRetirement().evaluate(
        strategy_version_id="s1",
        current_state=StrategyLifecycleState.RETIRED,
        evaluation=evaluation(),
    )
    assert report.action is StrategyRetirementAction.HOLD
    assert report.reasons == ("already_retired",)


def test_review_is_held() -> None:
    report = AutonomousStrategyRetirement().evaluate(
        strategy_version_id="s1",
        current_state=StrategyLifecycleState.ACTIVE,
        evaluation=evaluation(
            status=StrategyEvaluationStatus.REVIEW,
            action=StrategyEvaluationAction.QUARANTINE,
            reasons=("insufficient_evaluation_sample",),
        ),
    )
    assert report.action is StrategyRetirementAction.HOLD
    assert not report.should_retire


def test_accepted_continue_is_held() -> None:
    report = AutonomousStrategyRetirement().evaluate(
        strategy_version_id="s1",
        current_state=StrategyLifecycleState.ACTIVE,
        evaluation=evaluation(
            status=StrategyEvaluationStatus.ACCEPT,
            action=StrategyEvaluationAction.CONTINUE,
            reasons=(),
        ),
    )
    assert report.action is StrategyRetirementAction.HOLD
    assert report.reasons == ("retirement_not_authorized",)


def test_identity_mismatch_is_blocked() -> None:
    report = AutonomousStrategyRetirement().evaluate(
        strategy_version_id="s2",
        current_state=StrategyLifecycleState.ACTIVE,
        evaluation=evaluation(strategy_id="s1"),
    )
    assert report.action is StrategyRetirementAction.BLOCK
    assert not report.safe
    assert report.reasons == ("strategy_identity_mismatch",)


def test_empty_strategy_id_is_rejected() -> None:
    with pytest.raises(ValueError, match="strategy_version_id is required"):
        AutonomousStrategyRetirement().evaluate(
            strategy_version_id=" ",
            current_state=StrategyLifecycleState.ACTIVE,
            evaluation=evaluation(),
        )


def test_reject_without_retirement_action_is_held() -> None:
    report = AutonomousStrategyRetirement().evaluate(
        strategy_version_id="s1",
        current_state=StrategyLifecycleState.ACTIVE,
        evaluation=evaluation(
            action=StrategyEvaluationAction.QUARANTINE,
            reasons=("manual_review_required",),
        ),
    )
    assert report.action is StrategyRetirementAction.HOLD
    assert not report.should_retire
