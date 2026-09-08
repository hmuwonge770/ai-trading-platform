"""Deterministic, bounded governance for autonomous strategy promotion."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from packages.promotion.domain import PromotionStage

from .promotion import PromotionReadinessReport, PromotionReadinessStatus
from .strategy_lifecycle import StrategyLifecycleState


class PromotionGovernanceAction(StrEnum):
    PROMOTE = "promote"
    HOLD = "hold"
    BLOCK = "block"


@dataclass(frozen=True, slots=True)
class PromotionGovernanceRequest:
    strategy_version_id: UUID
    current_state: StrategyLifecycleState
    readiness: PromotionReadinessReport
    target_stage: PromotionStage
    risk_approved: bool = True
    capital_approved: bool = True


@dataclass(frozen=True, slots=True)
class PromotionGovernanceReport:
    strategy_version_id: UUID
    target_stage: PromotionStage
    action: PromotionGovernanceAction
    safe: bool
    reasons: tuple[str, ...] = ()

    @property
    def should_promote(self) -> bool:
        return self.action is PromotionGovernanceAction.PROMOTE


class AutonomousPromotionGovernance:
    """Plan a promotion decision without mutating lifecycle or authorization state."""

    def evaluate(self, request: PromotionGovernanceRequest) -> PromotionGovernanceReport:
        reasons: list[str] = []

        if request.readiness.strategy_version_id != request.strategy_version_id:
            return PromotionGovernanceReport(
                request.strategy_version_id,
                request.target_stage,
                PromotionGovernanceAction.BLOCK,
                False,
                ("strategy_identity_mismatch",),
            )

        if request.readiness.target_stage is not request.target_stage:
            return PromotionGovernanceReport(
                request.strategy_version_id,
                request.target_stage,
                PromotionGovernanceAction.BLOCK,
                False,
                ("target_stage_mismatch",),
            )

        if request.current_state in {
            StrategyLifecycleState.RETIRED,
            StrategyLifecycleState.QUARANTINED,
        }:
            reasons.append(f"strategy_{request.current_state.value}")

        if request.readiness.status is PromotionReadinessStatus.BLOCKED:
            reasons.extend(request.readiness.reasons or ("promotion_readiness_blocked",))
        elif request.readiness.status is PromotionReadinessStatus.REVIEW:
            reasons.extend(request.readiness.reasons or ("promotion_readiness_requires_review",))

        if not request.risk_approved:
            reasons.append("risk_governance_not_approved")
        if not request.capital_approved:
            reasons.append("capital_governance_not_approved")

        if reasons:
            action = PromotionGovernanceAction.BLOCK if (
                request.current_state in {StrategyLifecycleState.RETIRED, StrategyLifecycleState.QUARANTINED}
                or request.readiness.status is PromotionReadinessStatus.BLOCKED
                or not request.risk_approved
                or not request.capital_approved
            ) else PromotionGovernanceAction.HOLD
            return PromotionGovernanceReport(
                request.strategy_version_id,
                request.target_stage,
                action,
                True,
                tuple(reasons),
            )

        return PromotionGovernanceReport(
            request.strategy_version_id,
            request.target_stage,
            PromotionGovernanceAction.PROMOTE,
            True,
            ("promotion_governance_approved",),
        )
