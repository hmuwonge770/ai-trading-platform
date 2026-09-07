from uuid import uuid4

import pytest

from packages.autonomy.promotion import (
    AutonomousPromotionReadinessGate,
    PromotionEvidence,
    PromotionReadinessPolicy,
    PromotionReadinessStatus,
)
from packages.autonomy.accounting import AccountingStatus
from packages.autonomy.performance import PerformanceStatus
from packages.autonomy.reconciliation import ReconciliationStatus
from packages.promotion.domain import PromotionStage, StrategyVersion


def strategy():
    return StrategyVersion(uuid4(), uuid4(), "a" * 64, {"name": "test"})


def healthy_evidence(version_id):
    return PromotionEvidence(
        strategy_version_id=version_id,
        reconciliation=ReconciliationStatus.HEALTHY,
        accounting=AccountingStatus.HEALTHY,
        performance=PerformanceStatus.HEALTHY,
    )


def test_healthy_testnet_evidence_is_ready():
    s = strategy()
    report = AutonomousPromotionReadinessGate().assess(s, healthy_evidence(s.strategy_version_id), PromotionStage.TESTNET)
    assert report.status is PromotionReadinessStatus.READY
    assert report.ready
    assert report.reasons == ()


def test_unhealthy_evidence_requires_review():
    s = strategy()
    evidence = PromotionEvidence(
        s.strategy_version_id,
        ReconciliationStatus.MISMATCH,
        AccountingStatus.HEALTHY,
        PerformanceStatus.HEALTHY,
    )
    report = AutonomousPromotionReadinessGate().assess(s, evidence, PromotionStage.TESTNET)
    assert report.status is PromotionReadinessStatus.REVIEW
    assert "reconciliation_mismatch" in report.reasons


def test_live_target_is_blocked_even_with_healthy_evidence():
    s = strategy()
    report = AutonomousPromotionReadinessGate().assess(s, healthy_evidence(s.strategy_version_id), PromotionStage.LIVE_CANARY)
    assert report.status is PromotionReadinessStatus.BLOCKED
    assert "target_stage_requires_existing_authorization" in report.reasons


def test_strategy_evidence_mismatch_is_rejected():
    s = strategy()
    with pytest.raises(ValueError, match="evidence strategy version"):
        AutonomousPromotionReadinessGate().assess(s, healthy_evidence(uuid4()), PromotionStage.TESTNET)


def test_recovery_failures_block_readiness_by_default():
    s = strategy()
    evidence = PromotionEvidence(
        s.strategy_version_id,
        ReconciliationStatus.HEALTHY,
        AccountingStatus.HEALTHY,
        PerformanceStatus.HEALTHY,
        recovery_failures=1,
    )
    report = AutonomousPromotionReadinessGate().assess(s, evidence, PromotionStage.TESTNET)
    assert report.status is PromotionReadinessStatus.REVIEW
    assert "recovery_failures_exceeded" in report.reasons


def test_live_canary_cannot_be_enabled_by_policy():
    with pytest.raises(ValueError, match="live-canary"):
        PromotionReadinessPolicy(allow_live_canary=True)
