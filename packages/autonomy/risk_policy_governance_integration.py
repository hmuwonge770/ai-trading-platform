"""Compose risk-policy governance with bounded capital allocation."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .capital_allocation import AutonomousCapitalAllocator, CapitalAllocationRequest
from .risk_policy_governance import (
    AutonomousRiskPolicyGovernance,
    RiskPolicy,
    RiskPolicyReport,
    RiskPolicyRequest,
)


@dataclass(frozen=True, slots=True)
class GovernedCapitalRiskReport:
    strategy_version_id: str
    approved: bool
    approved_notional: Decimal
    risk_report: RiskPolicyReport
    capital_capacity: Decimal


class AutonomousCapitalRiskGovernance:
    """Apply risk policy and capital ceilings without widening either boundary."""

    def __init__(
        self,
        risk_governance: AutonomousRiskPolicyGovernance | None = None,
        allocator: AutonomousCapitalAllocator | None = None,
    ) -> None:
        self._risk = risk_governance or AutonomousRiskPolicyGovernance()
        self._allocator = allocator or AutonomousCapitalAllocator()

    def evaluate(
        self,
        *,
        policy: RiskPolicy,
        strategy_version_id: str,
        existing_total_exposure: Decimal,
        existing_strategy_exposure: Decimal,
        requested_notional: Decimal,
        portfolio_ceiling: Decimal,
        strategy_ceiling: Decimal,
    ) -> GovernedCapitalRiskReport:
        risk_report = self._risk.evaluate(
            policy,
            RiskPolicyRequest(
                strategy_version_id=strategy_version_id,
                existing_total_exposure=existing_total_exposure,
                existing_strategy_exposure=existing_strategy_exposure,
                requested_notional=requested_notional,
            ),
        )
        capital = self._allocator.evaluate(
            CapitalAllocationRequest(
                strategy_version_id=strategy_version_id,
                portfolio_ceiling=portfolio_ceiling,
                strategy_ceiling=strategy_ceiling,
                existing_exposure=existing_total_exposure,
                requested_capital=risk_report.approved_notional,
            )
        )
        approved = min(risk_report.approved_notional, capital.approved_allocation)
        return GovernedCapitalRiskReport(
            strategy_version_id=risk_report.strategy_version_id,
            approved=risk_report.approved and capital.safe and approved == requested_notional,
            approved_notional=approved,
            risk_report=risk_report,
            capital_capacity=capital.portfolio_capacity,
        )
