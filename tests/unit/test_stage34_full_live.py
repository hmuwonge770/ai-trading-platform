from decimal import Decimal
from uuid import uuid4

import pytest

from packages.promotion import (
    CapitalAllocation,
    FullLiveController,
    FullLiveEvidence,
    FullLiveGate,
    LiveAuthorization,
    Promotion,
    PromotionStage,
    StrategyVersion,
)
from packages.promotion.domain import PromotionStatus


FINGERPRINT = "a" * 64
RISK_FINGERPRINT = "b" * 64
AUTH_HASH = "c" * 64


def make_promotion() -> Promotion:
    return Promotion(
        strategy_version=StrategyVersion(uuid4(), uuid4(), FINGERPRINT, {"symbol": "BTCUSDT"}),
        from_stage=PromotionStage.LIVE_LIMITED,
        to_stage=PromotionStage.LIVE,
        requested_by="operator",
        capital_allocation=CapitalAllocation(
            PromotionStage.LIVE,
            Decimal("1000"),
            Decimal("100"),
            Decimal("30"),
            10,
        ),
    )


def make_authorization(promotion: Promotion) -> LiveAuthorization:
    return LiveAuthorization(
        promotion_id=str(promotion.promotion_id),
        strategy_version_id=str(promotion.strategy_version.strategy_version_id),
        strategy_fingerprint=FINGERPRINT,
        risk_policy_fingerprint=RISK_FINGERPRINT,
        capital=Decimal("1000"),
        max_position_value=Decimal("100"),
        max_daily_loss=Decimal("30"),
        max_orders_per_day=10,
        evidence_snapshot_hash="d" * 64,
        authorization_hash=AUTH_HASH,
        approved_by=("admin", "risk"),
    )


def full_evidence() -> FullLiveEvidence:
    return FullLiveEvidence(
        canary_passed=True,
        limited_live_passed=True,
        account_healthy=True,
        reconciliation_healthy=True,
        circuit_breaker_closed=True,
        kill_switch_disabled=True,
        live_armed=True,
        credentials_configured=True,
    )


def approve(promotion: Promotion) -> None:
    from packages.promotion.domain import Approval, ApprovalDecision, ApprovalRole

    for approver, role in (("risk", ApprovalRole.RISK_MANAGER), ("admin", ApprovalRole.ADMIN)):
        promotion.add_approval(
            Approval(
                approver_id=approver,
                role=role,
                decision=ApprovalDecision.APPROVE,
                fingerprint=FINGERPRINT,
                capital_limit=Decimal("1000"),
                evidence_hash="e" * 64,
            )
        )


def test_full_live_passes_only_when_every_gate_is_green():
    promotion = make_promotion()
    approve(promotion)
    authorization = make_authorization(promotion)

    report = FullLiveGate.evaluate(
        promotion=promotion,
        authorization=authorization,
        strategy_version_id=str(promotion.strategy_version.strategy_version_id),
        strategy_fingerprint=FINGERPRINT,
        approved_capital=Decimal("1000"),
        risk_policy_fingerprint=RISK_FINGERPRINT,
        evidence=full_evidence(),
    )

    assert report.passed
    assert report.failures == ()


def test_full_live_fails_closed_when_any_required_gate_is_missing():
    promotion = make_promotion()
    approve(promotion)
    authorization = make_authorization(promotion)
    evidence = full_evidence()
    evidence = FullLiveEvidence(**{**evidence.__dict__, "kill_switch_disabled": False})

    report = FullLiveGate.evaluate(
        promotion=promotion,
        authorization=authorization,
        strategy_version_id=str(promotion.strategy_version.strategy_version_id),
        strategy_fingerprint=FINGERPRINT,
        approved_capital=Decimal("1000"),
        risk_policy_fingerprint=RISK_FINGERPRINT,
        evidence=evidence,
    )

    assert not report.passed
    assert "Kill switch must be deliberately disabled" in report.failures


def test_full_live_rejects_wrong_production_endpoint():
    promotion = make_promotion()
    approve(promotion)
    authorization = make_authorization(promotion)
    evidence = FullLiveEvidence(**{**full_evidence().__dict__, "production_endpoint": "https://testnet.binance.vision"})

    report = FullLiveGate.evaluate(
        promotion=promotion,
        authorization=authorization,
        strategy_version_id=str(promotion.strategy_version.strategy_version_id),
        strategy_fingerprint=FINGERPRINT,
        approved_capital=Decimal("1000"),
        risk_policy_fingerprint=RISK_FINGERPRINT,
        evidence=evidence,
    )

    assert not report.passed
    assert "Production endpoint must be the approved Binance endpoint" in report.failures


def test_controller_cannot_activate_with_failed_gate():
    promotion = make_promotion()
    approve(promotion)
    authorization = make_authorization(promotion)
    controller = FullLiveController()

    with pytest.raises(PermissionError, match="gate has not passed"):
        controller.activate(
            promotion=promotion,
            authorization=authorization,
            gate=FullLiveGate.evaluate(
                promotion=promotion,
                authorization=authorization,
                strategy_version_id=str(promotion.strategy_version.strategy_version_id),
                strategy_fingerprint=FINGERPRINT,
                approved_capital=Decimal("1000"),
                risk_policy_fingerprint=RISK_FINGERPRINT,
                evidence=FullLiveEvidence(),
            ),
        )
    assert not controller.active
    assert promotion.status == PromotionStatus.APPROVED


def test_controller_activation_binds_authorization_and_halt_clears_it():
    promotion = make_promotion()
    approve(promotion)
    authorization = make_authorization(promotion)
    report = FullLiveGate.evaluate(
        promotion=promotion,
        authorization=authorization,
        strategy_version_id=str(promotion.strategy_version.strategy_version_id),
        strategy_fingerprint=FINGERPRINT,
        approved_capital=Decimal("1000"),
        risk_policy_fingerprint=RISK_FINGERPRINT,
        evidence=full_evidence(),
    )
    controller = FullLiveController()
    controller.activate(promotion=promotion, authorization=authorization, gate=report)

    assert controller.active
    assert controller.authorization_hash == AUTH_HASH
    assert promotion.status == PromotionStatus.ACTIVE

    controller.halt(promotion)
    assert not controller.active
    assert controller.authorization_hash is None
