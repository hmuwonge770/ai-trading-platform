import pytest

from packages.promotion.canary import CanaryController, CanaryLimits
from packages.promotion.domain import ApprovalRole, CapitalAllocation, PromotionStage, StrategyVersion
from packages.promotion.service import PromotionService
from packages.promotion.canary_gate import CanaryGateReport
from decimal import Decimal
from uuid import uuid4


def test_canary_requires_authorization_hash():
    service = PromotionService()
    promotion = service.request(
        strategy_version=StrategyVersion(uuid4(), uuid4(), "a" * 64, {}),
        from_stage=PromotionStage.TESTNET,
        to_stage=PromotionStage.LIVE_CANARY,
        requested_by="operator",
        capital_allocation=CapitalAllocation(PromotionStage.LIVE_CANARY, Decimal("100"), Decimal("50"), Decimal("10"), 5),
        evidence={},
    )
    service.approve(promotion, approver_id="risk", role=ApprovalRole.RISK_MANAGER, capital_limit=Decimal("100"), evidence={})
    service.approve(promotion, approver_id="admin", role=ApprovalRole.ADMIN, capital_limit=Decimal("100"), evidence={})
    canary = CanaryController()
    with pytest.raises(ValueError):
        canary.arm(promotion, CanaryLimits(Decimal("10"), Decimal("5"), Decimal("1"), 1), authorization_hash="bad")

    canary.arm(promotion, CanaryLimits(Decimal("10"), Decimal("5"), Decimal("1"), 1), authorization_hash="a" * 64)
    canary.start(promotion, gate=CanaryGateReport())
    assert canary.authorization_hash == "a" * 64
