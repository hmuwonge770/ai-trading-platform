from uuid import uuid4

import pytest

from packages.autonomy.accounting import AccountingStatus
from packages.autonomy.performance import PerformanceStatus
from packages.autonomy.promotion import PromotionEvidence, PromotionReadinessGate
from packages.autonomy.promotion_integration import (
    AutonomousPromotionWorkflowIntegration,
    PromotionHandoffStatus,
)
from packages.autonomy.reconciliation import ReconciliationStatus
from packages.promotion.domain import PromotionStage, StrategyVersion


def strategy():
    return StrategyVersion(uuid4(), uuid4(), "a" * 64, {"name": "test"})


def evidence(version_id):
    return PromotionEvidence(
        strategy_version_id=version_id,
        reconciliation=ReconciliationStatus.HEALTHY,
        accounting=AccountingStatus.HEALTHY,
        performance=PerformanceStatus.HEALTHY,
    )


def test_healthy_testnet_readiness_creates_non_live_handoff():
    s = strategy()
    e = evidence(s.strategy_version_id)
    report = PromotionReadinessGate().assess(s, e, PromotionStage.TESTNET)
    binding = AutonomousPromotionWorkflowIntegration().bind(s, e, report)

    assert binding.handoff_status is PromotionHandoffStatus.READY_FOR_NON_LIVE_WORKFLOW
    assert len(binding.evidence_hash) == 64


def test_healthy_live_evidence_requires_human_review():
    s = strategy()
    e = evidence(s.strategy_version_id)
    report = PromotionReadinessGate().assess(s, e, PromotionStage.LIVE_CANARY)
    binding = AutonomousPromotionWorkflowIntegration().bind(s, e, report)

    assert binding.handoff_status is PromotionHandoffStatus.HUMAN_REVIEW_REQUIRED
    assert binding.readiness_status.value == "blocked"


def test_unhealthy_live_evidence_remains_blocked():
    s = strategy()
    e = PromotionEvidence(
        s.strategy_version_id,
        ReconciliationStatus.MISMATCH,
        AccountingStatus.HEALTHY,
        PerformanceStatus.HEALTHY,
    )
    report = PromotionReadinessGate().assess(s, e, PromotionStage.LIVE_CANARY)
    binding = AutonomousPromotionWorkflowIntegration().bind(s, e, report)

    assert binding.handoff_status is PromotionHandoffStatus.BLOCKED


def test_mismatched_report_is_rejected():
    s = strategy()
    e = evidence(s.strategy_version_id)
    other = strategy()
    report = PromotionReadinessGate().assess(other, evidence(other.strategy_version_id), PromotionStage.TESTNET)

    with pytest.raises(ValueError, match="readiness report strategy version"):
        AutonomousPromotionWorkflowIntegration().bind(s, e, report)
