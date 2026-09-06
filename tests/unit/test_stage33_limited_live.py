from decimal import Decimal
from uuid import uuid4

import pytest

from packages.promotion import (
    ApprovalDecision,
    ApprovalRole,
    Approval,
    CapitalAllocation,
    CanaryGateReport,
    LimitedLiveController,
    LimitedLiveLimits,
    LimitedLiveState,
    Promotion,
    PromotionStage,
    StrategyVersion,
)


FINGERPRINT = "a" * 64
AUTH_HASH = "b" * 64
EVIDENCE = "c" * 64


def make_promotion() -> Promotion:
    strategy = StrategyVersion(uuid4(), uuid4(), FINGERPRINT, {"symbol": "BTCUSDT"})
    promotion = Promotion(
        strategy_version=strategy,
        from_stage=PromotionStage.LIVE_CANARY,
        to_stage=PromotionStage.LIVE_LIMITED,
        requested_by="requester",
        capital_allocation=CapitalAllocation(
            PromotionStage.LIVE_LIMITED,
            Decimal("1000"),
            Decimal("500"),
            Decimal("100"),
            20,
        ),
    )
    for approver, role in (("risk", ApprovalRole.RISK_MANAGER), ("admin", ApprovalRole.ADMIN)):
        promotion.add_approval(
            Approval(
                approver_id=approver,
                role=role,
                decision=ApprovalDecision.APPROVE,
                fingerprint=FINGERPRINT,
                capital_limit=Decimal("1000"),
                evidence_hash=EVIDENCE,
            )
        )
    return promotion


def limits(capital: str = "250") -> LimitedLiveLimits:
    return LimitedLiveLimits(Decimal(capital), Decimal("100"), Decimal("25"), 5)


def test_arm_requires_approved_limited_live_promotion():
    controller = LimitedLiveController()
    promotion = make_promotion()
    controller.arm(promotion, limits(), authorization_hash=AUTH_HASH)
    assert controller.state == LimitedLiveState.ARMED
    assert controller.authorization_hash == AUTH_HASH


def test_start_requires_clean_gate():
    controller = LimitedLiveController()
    promotion = make_promotion()
    controller.arm(promotion, limits(), authorization_hash=AUTH_HASH)
    with pytest.raises(PermissionError):
        controller.start(promotion, gate=CanaryGateReport(risk_violations=1))
    assert controller.state == LimitedLiveState.ARMED


def test_start_activates_only_with_clean_gate():
    controller = LimitedLiveController()
    promotion = make_promotion()
    controller.arm(promotion, limits(), authorization_hash=AUTH_HASH)
    gate = CanaryGateReport()
    controller.start(promotion, gate=gate)
    assert controller.state == LimitedLiveState.ACTIVE
    assert promotion.status.value == "active"
    assert controller.last_gate == gate


def test_scale_requires_fresh_clean_gate_and_never_increases_approved_allocation():
    controller = LimitedLiveController()
    promotion = make_promotion()
    controller.arm(promotion, limits(), authorization_hash=AUTH_HASH)
    controller.start(promotion, gate=CanaryGateReport())
    with pytest.raises(PermissionError):
        controller.scale(new_limits=limits("300"), gate=CanaryGateReport(critical_execution_errors=1))
    with pytest.raises(ValueError):
        controller.scale(new_limits=LimitedLiveLimits(Decimal("1500"), Decimal("100"), Decimal("25"), 5), gate=CanaryGateReport())
    controller.scale(new_limits=limits("300"), gate=CanaryGateReport())
    assert controller.limits is not None
    assert controller.limits.max_capital == Decimal("300")


def test_halt_and_disarm_clear_live_controls():
    controller = LimitedLiveController()
    promotion = make_promotion()
    controller.arm(promotion, limits(), authorization_hash=AUTH_HASH)
    controller.start(promotion, gate=CanaryGateReport())
    controller.halt(promotion)
    assert controller.state == LimitedLiveState.HALTED
    controller.disarm()
    assert controller.state == LimitedLiveState.DISARMED
    assert controller.limits is None
    assert controller.authorization_hash is None
