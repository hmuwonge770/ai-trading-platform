"""Compose promotion governance with immutable risk and capital boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from packages.promotion.domain import PromotionStage

from .capital_allocation_governance import AutonomousCapitalAllocationGovernance, CapitalGovernanceContext
from .promotion import PromotionReadinessReport
from .promotion_governance import (
    AutonomousPromotionGovernance,
    PromotionGovernanceAction,
    PromotionGovernanceReport,
    PromotionGovernanceRequest,
)
from .risk_policy_governance import RiskPolicy
from .strategy_lifecycle import StrategyLifecycleState


@dataclass(frozen=True, slots=True)
class GovernedPromotionReport:
    strategy_version_id: UUID
    promotion: PromotionGovernanceReport
    risk_approved: bool
    capital_approved: bool


class AutonomousPromotionGovernanceIntegration:
    """Require promotion readiness, risk, and capital governance together."""

    def __init__(
        self,
        promotion_governance: AutonomousPromotionGovernance | None = None,
        capital_governance: AutonomousCapitalAllocationGovernance | None = None,
    ) -> None:
        self._promotion = promotion_governance or AutonomousPromotionGovernance()
        self._capital = capital_governance or AutonomousCapitalAllocationGovernance()

    def evaluate(
        self,
        *,
        strategy_version_id: UUID,
        current_state: StrategyLifecycleState,
        readiness: PromotionReadinessReport,
        target_stage: PromotionStage,
        risk_policy: RiskPolicy,
        existing_total_exposure: Decimal,
        existing_strategy_exposure: Decimal,
        requested_notional: Decimal,
        portfolio_ceiling: Decimal,
        strategy_ceiling: Decimal,
    ) -> GovernedPromotionReport:
        capital = self._capital.evaluate(
            strategy_version_id=str(strategy_version_id),
            context=CapitalGovernanceContext(
                portfolio_ceiling=portfolio_ceiling,
                strategy_ceiling=strategy_ceiling,
                risk_ceiling=risk_policy.max_total_exposure,
            ),
            existing_exposure=existing_total_exposure,
            requested_capital=requested_notional,
        )
        risk_approved = requested_notional <= risk_policy.max_single_order_notional and requested_notional >= 0
        capital_approved = capital.safe and capital.approved_allocation == requested_notional
        promotion = self._promotion.evaluate(
            PromotionGovernanceRequest(
                strategy_version_id=strategy_version_id,
                current_state=current_state,
                readiness=readiness,
                target_stage=target_stage,
                risk_approved=risk_approved,
                capital_approved=capital_approved,
            )
        )
        if promotion.action is PromotionGovernanceAction.PROMOTE and not (risk_approved and capital_approved):
            promotion = PromotionGovernanceReport(
                strategy_version_id,
                target_stage,
                PromotionGovernanceAction.BLOCK,
                False,
                ("risk_or_capital_governance_failed",),
            )
        return GovernedPromotionReport(
            strategy_version_id,
            promotion,
            risk_approved,
            capital_approved,
        )
