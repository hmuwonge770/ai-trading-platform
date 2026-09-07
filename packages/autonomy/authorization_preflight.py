"""Read-only preflight for human-authorized live promotion.

This module verifies that an existing live promotion is consistent with the
immutable autonomous evidence handoff. It never approves, activates, or
mutates a promotion.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from packages.promotion.domain import LIVE_STAGES, ApprovalDecision, Promotion, PromotionStatus, StrategyVersion

from .promotion_integration import PromotionEvidenceBinding, PromotionHandoffStatus


class AuthorizationPreflightStatus(StrEnum):
    READY_FOR_HUMAN_AUTHORIZATION = "ready_for_human_authorization"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class AuthorizationPreflightReport:
    status: AuthorizationPreflightStatus
    promotion_id: UUID
    evidence_hash: str
    reasons: tuple[str, ...]

    @property
    def ready(self) -> bool:
        return self.status is AuthorizationPreflightStatus.READY_FOR_HUMAN_AUTHORIZATION


class AutonomousLiveAuthorizationPreflight:
    """Validate a live promotion before independent human authorization."""

    def assess(self, promotion: Promotion, binding: PromotionEvidenceBinding) -> AuthorizationPreflightReport:
        reasons: list[str] = []
        strategy: StrategyVersion = promotion.strategy_version

        strategy.validate()
        if promotion.status is not PromotionStatus.PENDING:
            reasons.append("promotion_not_pending")
        if promotion.to_stage not in LIVE_STAGES:
            reasons.append("target_stage_not_live")
        if binding.handoff_status is not PromotionHandoffStatus.HUMAN_REVIEW_REQUIRED:
            reasons.append("evidence_handoff_not_for_human_review")
        if binding.strategy_version_id != strategy.strategy_version_id:
            reasons.append("strategy_version_mismatch")
        if binding.strategy_fingerprint != strategy.fingerprint:
            reasons.append("strategy_fingerprint_mismatch")
        if binding.target_stage is not promotion.to_stage:
            reasons.append("target_stage_mismatch")
        if not binding.evidence_hash or len(binding.evidence_hash) != 64:
            reasons.append("invalid_evidence_hash")

        for approval in promotion.approvals:
            if approval.decision is ApprovalDecision.APPROVE and approval.evidence_hash != binding.evidence_hash:
                reasons.append("approval_evidence_hash_mismatch")
                break

        status = (
            AuthorizationPreflightStatus.BLOCKED
            if reasons
            else AuthorizationPreflightStatus.READY_FOR_HUMAN_AUTHORIZATION
        )
        return AuthorizationPreflightReport(status, promotion.promotion_id, binding.evidence_hash, tuple(reasons))
