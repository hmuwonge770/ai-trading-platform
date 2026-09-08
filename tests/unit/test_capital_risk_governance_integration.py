from decimal import Decimal

import pytest

from packages.autonomy.risk_policy_governance import RiskPolicy
from packages.autonomy.risk_policy_governance_integration import AutonomousCapitalRiskGovernance


def test_risk_and_capital_boundaries_are_both_enforced():
    report = AutonomousCapitalRiskGovernance().evaluate(
        policy=RiskPolicy(Decimal("1000"), Decimal("400"), Decimal("150")),
        strategy_version_id="strategy-v1",
        existing_total_exposure=Decimal("100"),
        existing_strategy_exposure=Decimal("50"),
        requested_notional=Decimal("200"),
        portfolio_ceiling=Decimal("220"),
        strategy_ceiling=Decimal("500"),
    )
    assert report.approved is False
    assert report.approved_notional == Decimal("120")


def test_tighter_risk_policy_never_widens_capital_capacity():
    report = AutonomousCapitalRiskGovernance().evaluate(
        policy=RiskPolicy(Decimal("1000"), Decimal("400"), Decimal("150")),
        strategy_version_id="strategy-v1",
        existing_total_exposure=Decimal("100"),
        existing_strategy_exposure=Decimal("50"),
        requested_notional=Decimal("100"),
        portfolio_ceiling=Decimal("1000"),
        strategy_ceiling=Decimal("400"),
    )
    assert report.approved_notional == Decimal("100")


def test_identity_failure_is_preserved():
    with pytest.raises(ValueError):
        AutonomousCapitalRiskGovernance().evaluate(
            policy=RiskPolicy(Decimal("100"), Decimal("50"), Decimal("25")),
            strategy_version_id=" ",
            existing_total_exposure=Decimal("0"),
            existing_strategy_exposure=Decimal("0"),
            requested_notional=Decimal("10"),
            portfolio_ceiling=Decimal("100"),
            strategy_ceiling=Decimal("50"),
        )


def test_governance_is_stateless_and_repeatable():
    governance = AutonomousCapitalRiskGovernance()
    args = dict(
        policy=RiskPolicy(Decimal("1000"), Decimal("400"), Decimal("150")),
        strategy_version_id="strategy-v1",
        existing_total_exposure=Decimal("100"),
        existing_strategy_exposure=Decimal("50"),
        requested_notional=Decimal("100"),
        portfolio_ceiling=Decimal("500"),
        strategy_ceiling=Decimal("300"),
    )
    assert governance.evaluate(**args) == governance.evaluate(**args)


def test_invalid_capital_input_fails_closed():
    with pytest.raises(ValueError):
        AutonomousCapitalRiskGovernance().evaluate(
            policy=RiskPolicy(Decimal("1000"), Decimal("400"), Decimal("150")),
            strategy_version_id="strategy-v1",
            existing_total_exposure=Decimal("0"),
            existing_strategy_exposure=Decimal("0"),
            requested_notional=Decimal("10"),
            portfolio_ceiling=Decimal("NaN"),
            strategy_ceiling=Decimal("100"),
        )
