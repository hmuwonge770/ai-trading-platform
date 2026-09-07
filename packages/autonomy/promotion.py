"""Read-only autonomous promotion readiness evaluation.

This module evaluates whether an immutable strategy has enough healthy evidence
for a requested promotion stage. It never creates or activates a promotion,
changes capital, or bypasses human authorization for live stages.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from packages.promotion.domain import PromotionStage, StrategyVersion

from .accounting import AccountingStatus
from .performance import PerformanceStatus
from .reconciliation import ReconciliationStatus


class PromotionReadinessStatus(StrEnum):
    READY = "ready"
    REVIEW = "review"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class PromotionEvidence:
    """Immutable evidence summary supplied by existing autonomous monitors."""

    strategy_version_id: UUID
    reconciliation: ReconciliationStatus
    accounting: AccountingStatus
    performance: PerformanceStatus
    recovery_failures: int = 0
    evidence_complete: bool = True

    def __post_init__(self) -> None:
        if self.recovery_failures < 0:
            raise ValueError("recovery_failures must be non-negative")


@dataclass(frozen=True, slots=True)
class PromotionReadinessPolicy:
    """Deterministic policy for autonomous readiness assessment."""

    allow_paper: bool = True
    allow_testnet: bool = True
    allow_live_canary: bool = False
    max_recovery_failures: int = 0

    def __post_init__(self) -> None:
        if self.max_recovery_failures < 0:
            raise ValueError("max_recovery_failures must be non-negative")
        if self.allow_live_canary:
            raise ValueError("autonomous live-canary readiness must remain disabled")


@dataclass(frozen=True, slots=True)
class PromotionReadinessReport:
    status: PromotionReadinessStatus
    strategy_version_id: UUID
    target_stage: PromotionStage
    reasons: tuple[str, ...]

    @property
    def ready(self) -> bool:
        return self.status is PromotionReadinessStatus.READY


class AutonomousPromotionReadinessGate:
    """Assess promotion readiness without mutating promotion state."""

    def __init__(self, *, policy: PromotionReadinessPolicy | None = None) -> None:
        self.policy = policy or PromotionReadinessPolicy()

    def assess(
        self,
        strategy: StrategyVersion,
        evidence: PromotionEvidence,
        target_stage: PromotionStage,
    ) -> PromotionReadinessReport:
        strategy.validate()
        if evidence.strategy_version_id != strategy.strategy_version_id:
            raise ValueError("evidence strategy version does not match strategy")

        reasons: list[str] = []
        if not evidence.evidence_complete:
            reasons.append("evidence_incomplete")
        if evidence.reconciliation is not ReconciliationStatus.HEALTHY:
            reasons.append(f"reconciliation_{evidence.reconciliation.value}")
        if evidence.accounting is not AccountingStatus.HEALTHY:
            reasons.append(f"accounting_{evidence.accounting.value}")
        if evidence.performance is not PerformanceStatus.HEALTHY:
            reasons.append(f"performance_{evidence.performance.value}")
        if evidence.recovery_failures > self.policy.max_recovery_failures:
            reasons.append("recovery_failures_exceeded")

        if target_stage is PromotionStage.PAPER and self.policy.allow_paper:
            allowed = True
        elif target_stage is PromotionStage.TESTNET and self.policy.allow_testnet:
            allowed = True
        else:
            allowed = False
            reasons.append("target_stage_requires_existing_authorization")

        if not allowed:
            status = PromotionReadinessStatus.BLOCKED
        elif reasons:
            status = PromotionReadinessStatus.REVIEW
        else:
            status = PromotionReadinessStatus.READY

        return PromotionReadinessReport(
            status=status,
            strategy_version_id=strategy.strategy_version_id,
            target_stage=target_stage,
            reasons=tuple(reasons),
        )
