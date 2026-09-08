from uuid import uuid4

import pytest

from packages.autonomy.promotion import PromotionReadinessReport, PromotionReadinessStatus
from packages.autonomy.promotion_governance import (
    AutonomousPromotionGovernance,
    PromotionGovernanceAction,
    PromotionGovernanceRequest,
)
from packages.autonomy.strategy_lifecycle import StrategyLifecycleState
from packages.promotion.domain import PromotionStage


def readiness(strategy_id, status=PromotionReadinessStatus.READY, stage=PromotionStage.TESTNET, reasons=()):
    return PromotionReadinessReport(status, strategy_id, stage, reasons)


def test_ready_strategy_can_be_promoted():
    strategy_id = uuid4()
    report = AutonomousPromotionGovernance().evaluate(
        PromotionGovernanceRequest(strategy_id, StrategyLifecycleState.CANDIDATE, readiness(strategy_id), PromotionStage.TESTNET)
    )
    assert report.action is PromotionGovernanceAction.PROMOTE
    assert report.should_promote
    assert report.safe


def test_identity_mismatch_blocks():
    strategy_id = uuid4()
    report = AutonomousPromotionGovernance().evaluate(
        PromotionGovernanceRequest(strategy_id, StrategyLifecycleState.CANDIDATE, readiness(uuid4()), PromotionStage.TESTNET)
    )
    assert report.action is PromotionGovernanceAction.BLOCK
    assert report.safe is False
    assert report.reasons == ("strategy_identity_mismatch",)


def test_target_stage_mismatch_blocks():
    strategy_id = uuid4()
    report = AutonomousPromotionGovernance().evaluate(
        PromotionGovernanceRequest(strategy_id, StrategyLifecycleState.CANDIDATE, readiness(strategy_id), PromotionStage.PAPER)
    )
    assert report.action is PromotionGovernanceAction.BLOCK
    assert report.reasons == ("target_stage_mismatch",)


@pytest.mark.parametrize("state", [StrategyLifecycleState.RETIRED, StrategyLifecycleState.QUARANTINED])
def test_retired_or_quarantined_strategy_cannot_be_promoted(state):
    strategy_id = uuid4()
    report = AutonomousPromotionGovernance().evaluate(
        PromotionGovernanceRequest(strategy_id, state, readiness(strategy_id), PromotionStage.TESTNET)
    )
    assert report.action is PromotionGovernanceAction.BLOCK
    assert f"strategy_{state.value}" in report.reasons


def test_readiness_review_holds():
    strategy_id = uuid4()
    report = AutonomousPromotionGovernance().evaluate(
        PromotionGovernanceRequest(
            strategy_id,
            StrategyLifecycleState.CANDIDATE,
            readiness(strategy_id, PromotionReadinessStatus.REVIEW, reasons=("performance_degraded",)),
            PromotionStage.TESTNET,
        )
    )
    assert report.action is PromotionGovernanceAction.HOLD
    assert report.safe
    assert report.reasons == ("performance_degraded",)


@pytest.mark.parametrize("risk_approved,capital_approved", [(False, True), (True, False), (False, False)])
def test_risk_or_capital_failure_blocks(risk_approved, capital_approved):
    strategy_id = uuid4()
    report = AutonomousPromotionGovernance().evaluate(
        PromotionGovernanceRequest(
            strategy_id,
            StrategyLifecycleState.CANDIDATE,
            readiness(strategy_id),
            PromotionStage.TESTNET,
            risk_approved=risk_approved,
            capital_approved=capital_approved,
        )
    )
    assert report.action is PromotionGovernanceAction.BLOCK
    assert report.safe


def test_identical_inputs_are_deterministic():
    strategy_id = uuid4()
    request = PromotionGovernanceRequest(
        strategy_id, StrategyLifecycleState.CANDIDATE, readiness(strategy_id), PromotionStage.TESTNET
    )
    first = AutonomousPromotionGovernance().evaluate(request)
    second = AutonomousPromotionGovernance().evaluate(request)
    assert first == second
