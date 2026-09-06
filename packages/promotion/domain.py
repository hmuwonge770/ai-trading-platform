from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
import hashlib
import json
from typing import Any
from uuid import UUID, uuid4


class PromotionStage(StrEnum):
    RESEARCH = "research"
    PAPER = "paper"
    TESTNET = "testnet"
    LIVE_CANARY = "live_canary"
    LIVE_LIMITED = "live_limited"
    LIVE = "live"


class PromotionStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ACTIVE = "active"
    HALTED = "halted"
    COMPLETED = "completed"


class ApprovalRole(StrEnum):
    RISK_MANAGER = "risk_manager"
    OPERATIONS = "operations"
    ADMIN = "admin"


class ApprovalDecision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"


LIVE_STAGES = {
    PromotionStage.LIVE_CANARY,
    PromotionStage.LIVE_LIMITED,
    PromotionStage.LIVE,
}


@dataclass(frozen=True)
class StrategyVersion:
    strategy_version_id: UUID
    strategy_id: UUID
    fingerprint: str
    configuration: dict[str, Any]
    frozen: bool = True

    def validate(self) -> None:
        if not self.frozen:
            raise ValueError("Only frozen strategy versions can be promoted")
        if len(self.fingerprint) != 64:
            raise ValueError("Strategy fingerprint must be a SHA-256 hex digest")
        try:
            int(self.fingerprint, 16)
        except ValueError as exc:
            raise ValueError("Strategy fingerprint must be hexadecimal") from exc


@dataclass(frozen=True)
class CapitalAllocation:
    environment: PromotionStage
    max_capital: Decimal
    max_position_value: Decimal
    max_daily_loss: Decimal
    max_orders_per_day: int
    enabled: bool = True

    def validate(self) -> None:
        if self.environment not in LIVE_STAGES:
            raise ValueError("Capital allocation for live authorization must target a live stage")
        if self.max_capital <= 0:
            raise ValueError("max_capital must be positive")
        if self.max_position_value <= 0 or self.max_position_value > self.max_capital:
            raise ValueError("max_position_value must be positive and <= max_capital")
        if self.max_daily_loss <= 0 or self.max_daily_loss > self.max_capital:
            raise ValueError("max_daily_loss must be positive and <= max_capital")
        if self.max_orders_per_day < 1:
            raise ValueError("max_orders_per_day must be positive")


@dataclass(frozen=True)
class Approval:
    approver_id: str
    role: ApprovalRole
    decision: ApprovalDecision
    fingerprint: str
    capital_limit: Decimal
    evidence_hash: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Promotion:
    strategy_version: StrategyVersion
    from_stage: PromotionStage
    to_stage: PromotionStage
    requested_by: str
    capital_allocation: CapitalAllocation
    required_approvals: int = 2
    promotion_id: UUID = field(default_factory=uuid4)
    status: PromotionStatus = PromotionStatus.PENDING
    approvals: list[Approval] = field(default_factory=list)
    evidence_snapshot_hash: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    activated_at: datetime | None = None
    halted_at: datetime | None = None

    def __post_init__(self) -> None:
        self.strategy_version.validate()
        self.capital_allocation.validate()
        if self.required_approvals < 2 and self.to_stage in LIVE_STAGES:
            raise ValueError("Live promotion requires at least two approvals")
        if self.to_stage not in LIVE_STAGES:
            raise ValueError("Stage 22 only authorizes live promotion stages")

    @property
    def distinct_approvers(self) -> set[str]:
        return {a.approver_id for a in self.approvals if a.decision == ApprovalDecision.APPROVE}

    @property
    def is_fully_approved(self) -> bool:
        return len(self.distinct_approvers) >= self.required_approvals

    def add_approval(self, approval: Approval) -> None:
        if approval.decision != ApprovalDecision.APPROVE:
            raise ValueError("Use reject() for rejection decisions")
        if approval.approver_id == self.requested_by:
            raise PermissionError("Requester cannot approve their own promotion")
        if any(a.approver_id == approval.approver_id for a in self.approvals):
            raise ValueError("Approver has already acted on this promotion")
        if approval.fingerprint != self.strategy_version.fingerprint:
            raise ValueError("Approval fingerprint does not match strategy version")
        if approval.capital_limit != self.capital_allocation.max_capital:
            raise ValueError("Approval capital limit does not match allocation")
        self.approvals.append(approval)
        if self.is_fully_approved:
            self.status = PromotionStatus.APPROVED

    def reject(self) -> None:
        if self.status == PromotionStatus.ACTIVE:
            raise ValueError("Active promotion must be halted, not rejected")
        self.status = PromotionStatus.REJECTED

    def activate(self) -> None:
        if self.status != PromotionStatus.APPROVED:
            raise ValueError("Promotion must have all required approvals before activation")
        self.status = PromotionStatus.ACTIVE
        self.activated_at = datetime.now(timezone.utc)

    def halt(self) -> None:
        if self.status != PromotionStatus.ACTIVE:
            raise ValueError("Only active promotions can be halted")
        self.status = PromotionStatus.HALTED
        self.halted_at = datetime.now(timezone.utc)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AuthorizationSnapshot:
    promotion_id: UUID
    strategy_version_id: UUID
    strategy_fingerprint: str
    environment: PromotionStage
    capital_allocation: CapitalAllocation
    approvals: tuple[Approval, ...]
    risk_policy_fingerprint: str
    evidence_snapshot_hash: str
    expires_at: datetime

    @property
    def authorization_hash(self) -> str:
        payload = {
            "promotion_id": str(self.promotion_id),
            "strategy_version_id": str(self.strategy_version_id),
            "strategy_fingerprint": self.strategy_fingerprint,
            "environment": self.environment.value,
            "capital": {
                "max_capital": str(self.capital_allocation.max_capital),
                "max_position_value": str(self.capital_allocation.max_position_value),
                "max_daily_loss": str(self.capital_allocation.max_daily_loss),
                "max_orders_per_day": self.capital_allocation.max_orders_per_day,
            },
            "approvals": sorted(
                [
                    {
                        "approver_id": a.approver_id,
                        "role": a.role.value,
                        "fingerprint": a.fingerprint,
                        "capital_limit": str(a.capital_limit),
                        "evidence_hash": a.evidence_hash,
                    }
                    for a in self.approvals
                ],
                key=lambda x: x["approver_id"],
            ),
            "risk_policy_fingerprint": self.risk_policy_fingerprint,
            "evidence_snapshot_hash": self.evidence_snapshot_hash,
            "expires_at": self.expires_at.isoformat(),
        }
        return sha256_hex(payload)
