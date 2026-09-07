from decimal import Decimal
from uuid import uuid4

from packages.autonomy.accounting import AccountingStatus
from packages.autonomy.authorization_preflight import (
    AuthorizationPreflightStatus,
    AutonomousLiveAuthorizationPreflight,
)
from packages.autonomy.performance import PerformanceStatus
from packages.autonomy.promotion import PromotionEvidence, PromotionReadinessReport, PromotionReadinessStatus
from packages.autonomy.promotion_integration import (
    AutonomousPromotionWorkflowIntegration,
    PromotionHandoffStatus,
)
from packages.autonomy.reconciliation import ReconciliationStatus
from packages.promotion.domain import CapitalAllocation, Promotion, PromotionStage, StrategyVersion


def strategy() -> StrategyVersion:
    return StrategyVersion(uuid4(), uuid4(), "a" * 64, {"name": "test"})


def binding_for(s: StrategyVersion):
    evidence = PromotionEvidence(
        strategy_version_id=s.strategy_version_id,
        reconciliation=ReconciliationStatus.HEALTHY,
        accounting=AccountingStatus.HEALTHY,
        performance=PerformanceStatus.HEALTHY,
    )
    report = PromotionReadinessReport(
        PromotionReadinessStatus.BLOCKED,
        s.strategy_version_id,
        PromotionStage.LIVE_CANARY,
        ("target_stage_requires_existing_authorization",),
    )
    binding = AutonomousPromotionWorkflowIntegration().bind(s, evidence, report)
    assert binding.handoff_status is PromotionHandoffStatus.HUMAN_REVIEW_REQUIRED
    return binding


def promotion_for(s: StrategyVersion) -> Promotion:
    return Promotion(
        strategy_version=s,
        from_stage=PromotionStage.TESTNET,
        to_stage=PromotionStage.LIVE_CANARY,
        requested_by="requester",
        capital_allocation=CapitalAllocation(
            PromotionStage.LIVE_CANARY,
            Decimal("1000"),
            Decimal("250"),
            Decimal("50"),
            10,
        ),
    )


def test_healthy_live_handoff_is_ready_for_human_authorization():
    s = strategy()
    report = AutonomousLiveAuthorizationPreflight().assess(promotion_for(s), binding_for(s))
    assert report.status is AuthorizationPreflightStatus.READY_FOR_HUMAN_AUTHORIZATION
    assert report.ready


def test_non_human_handoff_is_blocked():
    s = strategy()
    binding = binding_for(s)
    blocked = binding.__class__(
        binding.strategy_version_id,
        binding.strategy_fingerprint,
        binding.target_stage,
        binding.readiness_status,
        PromotionHandoffStatus.BLOCKED,
        binding.evidence_hash,
        binding.reasons,
    )
    report = AutonomousLiveAuthorizationPreflight().assess(promotion_for(s), blocked)
    assert report.status is AuthorizationPreflightStatus.BLOCKED
    assert "evidence_handoff_not_for_human_review" in report.reasons


def test_strategy_fingerprint_mismatch_is_blocked():
    s = strategy()
    binding = binding_for(s)
    other = strategy()
    report = AutonomousLiveAuthorizationPreflight().assess(promotion_for(other), binding)
    assert report.status is AuthorizationPreflightStatus.BLOCKED
    assert "strategy_version_mismatch" in report.reasons


def test_existing_approval_with_different_evidence_is_blocked():
    s = strategy()
    promotion = promotion_for(s)
    from packages.promotion.domain import Approval, ApprovalDecision, ApprovalRole

    promotion.approvals.append(
        Approval(
            approver_id="risk",
            role=ApprovalRole.RISK_MANAGER,
            decision=ApprovalDecision.APPROVE,
            fingerprint=s.fingerprint,
            capital_limit=Decimal("1000"),
            evidence_hash="b" * 64,
        )
    )
    report = AutonomousLiveAuthorizationPreflight().assess(promotion, binding_for(s))
    assert report.status is AuthorizationPreflightStatus.BLOCKED
    assert "approval_evidence_hash_mismatch" in report.reasons
