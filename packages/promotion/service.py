from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from .domain import (
    Approval,
    ApprovalDecision,
    ApprovalRole,
    AuthorizationSnapshot,
    CapitalAllocation,
    LIVE_STAGES,
    Promotion,
    PromotionStage,
    PromotionStatus,
    StrategyVersion,
    sha256_hex,
)


REQUIRED_LIVE_ROLES = {ApprovalRole.RISK_MANAGER, ApprovalRole.ADMIN}


class PromotionService:
    """Application service enforcing promotion policy in memory.

    Persistence adapters can wrap these methods in a SERIALIZABLE transaction
    and lock the promotion row. The domain rules remain deterministic.
    """

    def request(
        self,
        *,
        strategy_version: StrategyVersion,
        from_stage: PromotionStage,
        to_stage: PromotionStage,
        requested_by: str,
        capital_allocation: CapitalAllocation,
        evidence: dict[str, Any],
    ) -> Promotion:
        if from_stage == PromotionStage.LIVE:
            raise ValueError("A LIVE strategy cannot be promoted further")
        if to_stage not in LIVE_STAGES:
            raise ValueError("Target must be a live promotion stage")
        if not requested_by:
            raise ValueError("requested_by is required")

        promotion = Promotion(
            strategy_version=strategy_version,
            from_stage=from_stage,
            to_stage=to_stage,
            requested_by=requested_by,
            capital_allocation=capital_allocation,
            evidence_snapshot_hash=sha256_hex(evidence),
        )
        return promotion

    def approve(
        self,
        promotion: Promotion,
        *,
        approver_id: str,
        role: ApprovalRole,
        capital_limit: Decimal,
        evidence: dict[str, Any],
    ) -> Promotion:
        if promotion.status != PromotionStatus.PENDING:
            raise ValueError(f"Promotion is not pending: {promotion.status}")
        if role not in REQUIRED_LIVE_ROLES:
            raise PermissionError(f"Role {role} cannot authorize live trading")

        evidence_hash = sha256_hex(evidence)
        approval = Approval(
            approver_id=approver_id,
            role=role,
            decision=ApprovalDecision.APPROVE,
            fingerprint=promotion.strategy_version.fingerprint,
            capital_limit=capital_limit,
            evidence_hash=evidence_hash,
        )
        promotion.add_approval(approval)

        if promotion.is_fully_approved:
            roles = {a.role for a in promotion.approvals}
            if not REQUIRED_LIVE_ROLES.issubset(roles):
                promotion.status = PromotionStatus.PENDING
        return promotion

    def reject(self, promotion: Promotion, *, approver_id: str) -> Promotion:
        if approver_id == promotion.requested_by:
            raise PermissionError("Requester cannot reject their own promotion")
        promotion.reject()
        return promotion

    def activate(self, promotion: Promotion) -> Promotion:
        roles = {a.role for a in promotion.approvals if a.decision == ApprovalDecision.APPROVE}
        if not REQUIRED_LIVE_ROLES.issubset(roles):
            raise PermissionError("Risk Manager and Admin approvals are required")
        promotion.activate()
        return promotion

    def halt(self, promotion: Promotion) -> Promotion:
        promotion.halt()
        return promotion

    def authorization(
        self,
        promotion: Promotion,
        *,
        risk_policy_fingerprint: str,
        ttl: timedelta = timedelta(minutes=15),
        now: datetime | None = None,
    ) -> AuthorizationSnapshot:
        now = now or datetime.now(timezone.utc)
        if promotion.status not in {PromotionStatus.APPROVED, PromotionStatus.ACTIVE}:
            raise PermissionError("Promotion is not authorized")
        if not promotion.is_fully_approved:
            raise PermissionError("Promotion lacks required approvals")
        roles = {a.role for a in promotion.approvals}
        if not REQUIRED_LIVE_ROLES.issubset(roles):
            raise PermissionError("Required independent roles are missing")
        if ttl <= timedelta(0):
            raise ValueError("Authorization TTL must be positive")

        return AuthorizationSnapshot(
            promotion_id=promotion.promotion_id,
            strategy_version_id=promotion.strategy_version.strategy_version_id,
            strategy_fingerprint=promotion.strategy_version.fingerprint,
            environment=promotion.to_stage,
            capital_allocation=promotion.capital_allocation,
            approvals=tuple(promotion.approvals),
            risk_policy_fingerprint=risk_policy_fingerprint,
            evidence_snapshot_hash=promotion.evidence_snapshot_hash,
            expires_at=now + ttl,
        )
