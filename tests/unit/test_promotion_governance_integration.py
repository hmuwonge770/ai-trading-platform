from decimal import Decimal
from uuid import uuid4

from packages.autonomy.promotion import PromotionReadinessReport, PromotionReadinessStatus
from packages.autonomy.promotion_governance import PromotionGovernanceAction
from packages.autonomy.promotion_governance_integration import AutonomousPromotionGovernanceIntegration
from packages.autonomy.risk_policy_governance import RiskPolicy
from packages.autonomy.strategy_lifecycle import StrategyLifecycleState
from packages.promotion.domain import PromotionStage


def test_promotion_requires_both_risk_and_capital_boundaries():
    strategy_id = uuid4()
    readiness = PromotionReadinessReport(
        PromotionReadinessStatus.READY, strategy_id, PromotionStage.TESTNET, ()
    )
    report = AutonomousPromotionGovernanceIntegration().evaluate(
        strategy_version_id=strategy_id,
        current_state=StrategyLifecycleState.CANDIDATE,
        readiness=readiness,
        target_stage=PromotionStage.TESTNET,
        risk_policy=RiskPolicy(Decimal("1000"), Decimal("500"), Decimal("100")),
        existing_total_exposure=Decimal("0"),
        existing_strategy_exposure=Decimal("0"),
        requested_notional=Decimal("100"),
        portfolio_ceiling=Decimal("1000"),
        strategy_ceiling=Decimal("500"),
    )
    assert report.promotion.action is PromotionGovernanceAction.PROMOTE
    assert report.risk_approved
    assert report.capital_approved


def test_tighter_risk_order_limit_blocks_promotion():
    strategy_id = uuid4()
    readiness = PromotionReadinessReport(
        PromotionReadinessStatus.READY, strategy_id, PromotionStage.TESTNET, ()
    )
    report = AutonomousPromotionGovernanceIntegration().evaluate(
        strategy_version_id=strategy_id,
        current_state=StrategyLifecycleState.CANDIDATE,
        readiness=readiness,
        target_stage=PromotionStage.TESTNET,
        risk_policy=RiskPolicy(Decimal("1000"), Decimal("500"), Decimal("50")),
        existing_total_exposure=Decimal("0"),
        existing_strategy_exposure=Decimal("0"),
        requested_notional=Decimal("100"),
        portfolio_ceiling=Decimal("1000"),
        strategy_ceiling=Decimal("500"),
    )
    assert report.promotion.action is PromotionGovernanceAction.BLOCK
    assert not report.risk_approved


def test_existing_exposure_reduces_available_capital():
    strategy_id = uuid4()
    readiness = PromotionReadinessReport(
        PromotionReadinessStatus.READY, strategy_id, PromotionStage.TESTNET, ()
    )
    report = AutonomousPromotionGovernanceIntegration().evaluate(
        strategy_version_id=strategy_id,
        current_state=StrategyLifecycleState.CANDIDATE,
        readiness=readiness,
        target_stage=PromotionStage.TESTNET,
        risk_policy=RiskPolicy(Decimal("1000"), Decimal("500"), Decimal("200")),
        existing_total_exposure=Decimal("950"),
        existing_strategy_exposure=Decimal("100"),
        requested_notional=Decimal("100"),
        portfolio_ceiling=Decimal("1000"),
        strategy_ceiling=Decimal("500"),
    )
    assert report.promotion.action is PromotionGovernanceAction.BLOCK
    assert not report.capital_approved


def test_governance_is_read_only():
    strategy_id = uuid4()
    readiness = PromotionReadinessReport(
        PromotionReadinessStatus.READY, strategy_id, PromotionStage.TESTNET, ()
    )
    policy = RiskPolicy(Decimal("1000"), Decimal("500"), Decimal("100"))
    report = AutonomousPromotionGovernanceIntegration().evaluate(
        strategy_version_id=strategy_id,
        current_state=StrategyLifecycleState.CANDIDATE,
        readiness=readiness,
        target_stage=PromotionStage.TESTNET,
        risk_policy=policy,
        existing_total_exposure=Decimal("0"),
        existing_strategy_exposure=Decimal("0"),
        requested_notional=Decimal("100"),
        portfolio_ceiling=Decimal("1000"),
        strategy_ceiling=Decimal("500"),
    )
    assert policy.max_total_exposure == Decimal("1000")
    assert policy.max_strategy_exposure == Decimal("500")
    assert report.promotion.safe
