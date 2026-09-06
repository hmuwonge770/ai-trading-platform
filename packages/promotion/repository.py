from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from .domain import (
    Approval,
    ApprovalDecision,
    ApprovalRole,
    AuthorizationSnapshot,
    CapitalAllocation,
    Promotion,
    PromotionStage,
    PromotionStatus,
    StrategyVersion,
)


@dataclass(frozen=True)
class PromotionRepository:
    """PostgreSQL persistence boundary for promotion authorization.

    Approval, activation and halt paths lock the promotion row with FOR UPDATE
    so concurrent operators cannot observe or commit conflicting lifecycle
    state. The repository never executes an exchange request.
    """

    db: Session

    def create(self, promotion: Promotion) -> Promotion:
        self.db.execute(text("""
            INSERT INTO strategy_promotions
                (id, strategy_version_id, from_stage, to_stage, requested_by,
                 status, required_approvals, evidence_snapshot_hash,
                 max_capital, max_position_value, max_daily_loss,
                 max_orders_per_day, allocation_enabled)
            VALUES (:id, :strategy_version_id, :from_stage, :to_stage, :requested_by,
                    :status, :required_approvals, :evidence_snapshot_hash,
                    :max_capital, :max_position_value, :max_daily_loss,
                    :max_orders_per_day, :allocation_enabled)
        """), self._promotion_params(promotion))
        self.db.execute(text("""
            INSERT INTO capital_allocations
                (id, strategy_version_id, environment, max_capital,
                 max_position_value, max_daily_loss, max_orders_per_day, enabled)
            VALUES (:id, :strategy_version_id, :environment, :max_capital,
                    :max_position_value, :max_daily_loss, :max_orders_per_day, :enabled)
            ON CONFLICT (strategy_version_id, environment)
            DO UPDATE SET max_capital = EXCLUDED.max_capital,
                          max_position_value = EXCLUDED.max_position_value,
                          max_daily_loss = EXCLUDED.max_daily_loss,
                          max_orders_per_day = EXCLUDED.max_orders_per_day,
                          enabled = EXCLUDED.enabled
        """), {
            "id": str(uuid4()),
            "strategy_version_id": str(promotion.strategy_version.strategy_version_id),
            "environment": promotion.to_stage.value,
            "max_capital": promotion.capital_allocation.max_capital,
            "max_position_value": promotion.capital_allocation.max_position_value,
            "max_daily_loss": promotion.capital_allocation.max_daily_loss,
            "max_orders_per_day": promotion.capital_allocation.max_orders_per_day,
            "enabled": promotion.capital_allocation.enabled,
        })
        self.db.commit()
        return promotion

    def get(self, promotion_id: UUID) -> Promotion | None:
        return self._find(promotion_id, lock=False)

    def get_for_update(self, promotion_id: UUID) -> Promotion | None:
        return self._find(promotion_id, lock=True)

    def add_approval(self, promotion_id: UUID, *, approver_id: str,
                     role: ApprovalRole, capital_limit: Decimal,
                     evidence_hash: str, fingerprint: str) -> Promotion:
        """Atomically lock, validate and persist one approval."""
        promotion = self.get_for_update(promotion_id)
        if promotion is None:
            raise LookupError("promotion not found")
        if promotion.status != PromotionStatus.PENDING:
            raise ValueError(f"Promotion is not pending: {promotion.status}")
        if role not in {ApprovalRole.RISK_MANAGER, ApprovalRole.ADMIN}:
            raise PermissionError(f"Role {role} cannot authorize live trading")
        approval = Approval(approver_id, role, ApprovalDecision.APPROVE,
                            fingerprint, capital_limit, evidence_hash)
        promotion.add_approval(approval)
        self.db.execute(text("""
            INSERT INTO promotion_approvals
                (id, promotion_id, approver_id, role, decision, fingerprint,
                 capital_limit, evidence_hash)
            VALUES (:id, :promotion_id, :approver_id, :role, :decision, :fingerprint,
                    :capital_limit, :evidence_hash)
        """), {
            "id": str(uuid4()), "promotion_id": str(promotion_id),
            "approver_id": approver_id, "role": role.value,
            "decision": ApprovalDecision.APPROVE.value, "fingerprint": fingerprint,
            "capital_limit": capital_limit, "evidence_hash": evidence_hash,
        })
        self.db.execute(text("UPDATE strategy_promotions SET status = :status WHERE id = :id"),
                        {"status": promotion.status.value, "id": str(promotion_id)})
        self.db.commit()
        return promotion

    def activate(self, promotion_id: UUID) -> Promotion:
        """Atomically require both independent approvals before activation."""
        promotion = self.get_for_update(promotion_id)
        if promotion is None:
            raise LookupError("promotion not found")
        rows = self.db.execute(text("""
            SELECT approver_id, role, decision, fingerprint, capital_limit, evidence_hash, created_at
            FROM promotion_approvals
            WHERE promotion_id = :promotion_id AND decision = 'approve'
            FOR UPDATE
        """), {"promotion_id": str(promotion_id)}).mappings().all()
        promotion.approvals = [self._approval(row) for row in rows]
        roles = {a.role for a in promotion.approvals}
        if not {ApprovalRole.RISK_MANAGER, ApprovalRole.ADMIN}.issubset(roles):
            raise PermissionError("Risk Manager and Admin approvals are required")
        promotion.status = PromotionStatus.APPROVED
        promotion.activate()
        self.db.execute(text("""
            UPDATE strategy_promotions SET status = 'active', activated_at = :activated_at
            WHERE id = :id
        """), {"activated_at": datetime.now(timezone.utc), "id": str(promotion_id)})
        self.db.commit()
        return promotion

    def halt(self, promotion_id: UUID) -> Promotion:
        """Atomically halt an active promotion."""
        promotion = self.get_for_update(promotion_id)
        if promotion is None:
            raise LookupError("promotion not found")
        promotion.halt()
        self.db.execute(text("""
            UPDATE strategy_promotions SET status = 'halted', halted_at = :halted_at
            WHERE id = :id
        """), {"halted_at": datetime.now(timezone.utc), "id": str(promotion_id)})
        self.db.commit()
        return promotion

    def save_authorization(self, snapshot: AuthorizationSnapshot) -> AuthorizationSnapshot:
        self.db.execute(text("""
            INSERT INTO authorization_snapshots
                (id, promotion_id, strategy_version_id, strategy_fingerprint,
                 environment, risk_policy_fingerprint, evidence_snapshot_hash,
                 authorization_hash, expires_at)
            VALUES (:id, :promotion_id, :strategy_version_id, :strategy_fingerprint,
                    :environment, :risk_policy_fingerprint, :evidence_snapshot_hash,
                    :authorization_hash, :expires_at)
        """), {
            "id": str(uuid4()), "promotion_id": str(snapshot.promotion_id),
            "strategy_version_id": str(snapshot.strategy_version_id),
            "strategy_fingerprint": snapshot.strategy_fingerprint,
            "environment": snapshot.environment.value,
            "risk_policy_fingerprint": snapshot.risk_policy_fingerprint,
            "evidence_snapshot_hash": snapshot.evidence_snapshot_hash,
            "authorization_hash": snapshot.authorization_hash,
            "expires_at": snapshot.expires_at,
        })
        self.db.commit()
        return snapshot

    def _find(self, promotion_id: UUID, *, lock: bool) -> Promotion | None:
        suffix = " FOR UPDATE" if lock else ""
        row = self.db.execute(
            text(f"SELECT * FROM strategy_promotions WHERE id = :id{suffix}"),
            {"id": str(promotion_id)},
        ).mappings().first()
        return None if row is None else self._load_promotion(row)

    @staticmethod
    def _promotion_params(promotion: Promotion) -> dict[str, Any]:
        allocation = promotion.capital_allocation
        return {
            "id": str(promotion.promotion_id),
            "strategy_version_id": str(promotion.strategy_version.strategy_version_id),
            "from_stage": promotion.from_stage.value, "to_stage": promotion.to_stage.value,
            "requested_by": promotion.requested_by, "status": promotion.status.value,
            "required_approvals": promotion.required_approvals,
            "evidence_snapshot_hash": promotion.evidence_snapshot_hash,
            "max_capital": allocation.max_capital, "max_position_value": allocation.max_position_value,
            "max_daily_loss": allocation.max_daily_loss, "max_orders_per_day": allocation.max_orders_per_day,
            "allocation_enabled": allocation.enabled,
        }

    @staticmethod
    def _approval(row: Any) -> Approval:
        return Approval(row["approver_id"], ApprovalRole(row["role"]), ApprovalDecision(row["decision"]),
                        row["fingerprint"], Decimal(str(row["capital_limit"])), row["evidence_hash"], row["created_at"])

    def _load_promotion(self, row: Any) -> Promotion:
        version_row = self.db.execute(
            text("SELECT id, strategy_id, fingerprint, config FROM strategy_versions WHERE id = :id"),
            {"id": str(row["strategy_version_id"])},
        ).mappings().first()
        if version_row is None:
            raise LookupError("strategy version not found")
        allocation = CapitalAllocation(
            environment=PromotionStage(row["to_stage"]),
            max_capital=Decimal(str(row["max_capital"])),
            max_position_value=Decimal(str(row["max_position_value"])),
            max_daily_loss=Decimal(str(row["max_daily_loss"])),
            max_orders_per_day=int(row["max_orders_per_day"]), enabled=bool(row["allocation_enabled"]),
        )
        approvals = self.db.execute(text("""
            SELECT approver_id, role, decision, fingerprint, capital_limit, evidence_hash, created_at
            FROM promotion_approvals WHERE promotion_id = :promotion_id ORDER BY created_at
        """), {"promotion_id": str(row["id"])}).mappings().all()
        strategy_version = StrategyVersion(
            strategy_version_id=UUID(str(version_row["id"])),
            strategy_id=UUID(str(version_row["strategy_id"])),
            fingerprint=str(version_row["fingerprint"]), configuration=dict(version_row["config"] or {}),
        )
        return Promotion(
            strategy_version=strategy_version, from_stage=PromotionStage(row["from_stage"]),
            to_stage=PromotionStage(row["to_stage"]), requested_by=row["requested_by"],
            capital_allocation=allocation, required_approvals=int(row["required_approvals"]),
            promotion_id=UUID(str(row["id"])), status=PromotionStatus(row["status"]),
            approvals=[self._approval(item) for item in approvals],
            evidence_snapshot_hash=row["evidence_snapshot_hash"], created_at=row["created_at"],
            activated_at=row["activated_at"], halted_at=row["halted_at"],
        )
