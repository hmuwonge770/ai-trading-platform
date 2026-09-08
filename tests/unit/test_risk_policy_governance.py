from decimal import Decimal

import pytest

from packages.autonomy.risk_policy_governance import (
    AutonomousRiskPolicyGovernance,
    RiskPolicy,
    RiskPolicyRequest,
)


def policy() -> RiskPolicy:
    return RiskPolicy(
        max_total_exposure=Decimal("1000"),
        max_strategy_exposure=Decimal("400"),
        max_single_order_notional=Decimal("150"),
    )


def request(**overrides) -> RiskPolicyRequest:
    values = {
        "strategy_version_id": "strategy-v1",
        "existing_total_exposure": Decimal("100"),
        "existing_strategy_exposure": Decimal("50"),
        "requested_notional": Decimal("100"),
    }
    values.update(overrides)
    return RiskPolicyRequest(**values)


def test_approves_within_all_limits():
    report = AutonomousRiskPolicyGovernance().evaluate(policy(), request())
    assert report.approved is True
    assert report.approved_notional == Decimal("100")


def test_tightest_order_limit_wins():
    report = AutonomousRiskPolicyGovernance().evaluate(policy(), request(requested_notional=Decimal("500")))
    assert report.approved is False
    assert report.approved_notional == Decimal("150")


def test_existing_strategy_exposure_is_deducted():
    report = AutonomousRiskPolicyGovernance().evaluate(
        policy(), request(existing_strategy_exposure=Decimal("350"), requested_notional=Decimal("100"))
    )
    assert report.approved_notional == Decimal("50")


def test_exhausted_total_capacity_fails_closed():
    report = AutonomousRiskPolicyGovernance().evaluate(
        policy(), request(existing_total_exposure=Decimal("1000"), requested_notional=Decimal("1"))
    )
    assert report.approved is False
    assert report.approved_notional == Decimal("0")


def test_identity_is_required():
    with pytest.raises(ValueError, match="strategy_identity_required"):
        AutonomousRiskPolicyGovernance().evaluate(policy(), request(strategy_version_id=""))


@pytest.mark.parametrize("field", ["existing_total_exposure", "existing_strategy_exposure", "requested_notional"])
def test_negative_inputs_fail_closed(field):
    with pytest.raises(ValueError):
        AutonomousRiskPolicyGovernance().evaluate(policy(), request(**{field: Decimal("-1")}))


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_inputs_fail_closed(value):
    with pytest.raises(ValueError):
        AutonomousRiskPolicyGovernance().evaluate(policy(), request(requested_notional=value))


def test_policy_cannot_be_widened_by_invalid_relationship():
    with pytest.raises(ValueError):
        RiskPolicy(Decimal("100"), Decimal("101"), Decimal("10"))


def test_identical_inputs_are_deterministic():
    governance = AutonomousRiskPolicyGovernance()
    first = governance.evaluate(policy(), request())
    second = governance.evaluate(policy(), request())
    assert first == second
