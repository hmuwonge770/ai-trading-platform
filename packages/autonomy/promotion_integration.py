"""Bind autonomous readiness evidence to the existing promotion workflow.

This module creates an immutable handoff record only. It never creates a
promotion, grants approval, allocates capital, or activates live trading.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from packages.promotion.domain import PromotionStage, StrategyVersion, canonical_json, sha256_hex

from .promotion import PromotionEvidence, PromotionReadinessReport, PromotionReadinessStatus


class PromotionHandoffStatus(StrEnum):
    READY_FOR_NON_LIVE_WORKFLOW = "ready_for_non_live_workflow"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class PromotionEvidenceBinding:
    """Immutable evidence handoff attached by a later promotion workflow."""

    strategy_version_id: UUID
    strategy_fingerprint: str
    target_stage: PromotionStage
    readiness_status: PromotionReadinessStatus
    handoff_status: PromotionHandoffStatus
    evidence_hash: str
    reasons: tuple[str, ...]


class AutonomousPromotionWorkflowIntegration:
    """Translate readiness evidence into a safe promotion-workflow handoff."""

    def bind(
        self,
        strategy: StrategyVersion,
        evidence: PromotionEvidence,
        report: PromotionReadinessReport,
    ) -> PromotionEvidenceBinding:
        strategy.validate()
        if evidence.strategy_version_id != strategy.strategy_version_id:
            raise ValueError("evidence strategy version does not match strategy")
        if report.strategy_version_id != strategy.strategy_version_id:
            raise ValueError("readiness report strategy version does not match strategy")
        if report.target_stage is not report.target_stage:
            raise ValueError("invalid target stage")

        if report.status is PromotionReadinessStatus.READY:
            handoff = PromotionHandoffStatus.READY_FOR_NON_LIVE_WORKFLOW
        elif report.target_stage in {
            PromotionStage.LIVE_CANARY,
            PromotionStage.LIVE_LIMITED,
            PromotionStage.LIVE,
        } and self._evidence_healthy(evidence):
            handoff = PromotionHandoffStatus.HUMAN_REVIEW_REQUIRED
        else:
            handoff = PromotionHandoffStatus.BLOCKED

        payload = {
            "strategy_version_id": str(strategy.strategy_version_id),
            "strategy_fingerprint": strategy.fingerprint,
            "target_stage": report.target_stage.value,
            "readiness_status": report.status.value,
            "handoff_status": handoff.value,
            "reasons": list(report.reasons),
            "evidence": {
                "reconciliation": evidence.reconciliation.value,
                "accounting": evidence.accounting.value,
                "performance": evidence.performance.value,
                "recovery_failures": evidence.recovery_failures,
                "evidence_complete": evidence.evidence_complete,
            },
        }
        return PromotionEvidenceBinding(
            strategy_version_id=strategy.strategy_version_id,
            strategy_fingerprint=strategy.fingerprint,
            target_stage=report.target_stage,
            readiness_status=report.status,
            handoff_status=handoff,
            evidence_hash=sha256_hex(canonical_json(payload)),
            reasons=report.reasons,
        )

    @staticmethod
    def _evidence_healthy(evidence: PromotionEvidence) -> bool:
        from .accounting import AccountingStatus
        from .performance import PerformanceStatus
        from .reconciliation import ReconciliationStatus

        return (
            evidence.evidence_complete
            and evidence.reconciliation is ReconciliationStatus.HEALTHY
            and evidence.accounting is AccountingStatus.HEALTHY
            and evidence.performance is PerformanceStatus.HEALTHY
            and evidence.recovery_failures == 0
        )
