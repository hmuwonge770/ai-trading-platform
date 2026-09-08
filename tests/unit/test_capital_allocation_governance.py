from decimal import Decimal

from packages.autonomy.capital_allocation_governance import (
    AutonomousCapitalAllocationGovernance,
    CapitalGovernanceContext,
)


def test_risk_ceiling_is_an_independent_hard_boundary() -> None:
    report = AutonomousCapitalAllocationGovernance().evaluate(
        strategy_version_id="s1",
        context=CapitalGovernanceContext(
            portfolio_ceiling=Decimal("5000"),
            strategy_ceiling=Decimal("2000"),
            risk_ceiling=Decimal("500"),
        ),
        existing_exposure=Decimal("100"),
        requested_capital=Decimal("1000"),
    )
    assert report.approved_allocation == Decimal("400")
    assert report.strategy_capacity == Decimal("400")


def test_governance_does_not_mutate_context() -> None:
    context = CapitalGovernanceContext(
        portfolio_ceiling=Decimal("1000"),
        strategy_ceiling=Decimal("600"),
        risk_ceiling=Decimal("300"),
    )
    AutonomousCapitalAllocationGovernance().evaluate(
        strategy_version_id="s1",
        context=context,
        existing_exposure=Decimal("50"),
        requested_capital=Decimal("900"),
    )
    assert context.portfolio_ceiling == Decimal("1000")
    assert context.strategy_ceiling == Decimal("600")
    assert context.risk_ceiling == Decimal("300")


def test_zero_risk_capacity_fails_to_zero_allocation() -> None:
    report = AutonomousCapitalAllocationGovernance().evaluate(
        strategy_version_id="s1",
        context=CapitalGovernanceContext(
            portfolio_ceiling=Decimal("1000"),
            strategy_ceiling=Decimal("800"),
            risk_ceiling=Decimal("100"),
        ),
        existing_exposure=Decimal("100"),
        requested_capital=Decimal("10"),
    )
    assert report.approved_allocation == Decimal("0")
    assert not report.can_allocate
    assert "strategy_ceiling_exhausted" in report.reasons
