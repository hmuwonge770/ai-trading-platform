from decimal import Decimal

import pytest

from packages.autonomy.capital_allocation import (
    AutonomousCapitalAllocator,
    CapitalAllocationRequest,
)


def request(**overrides: object) -> CapitalAllocationRequest:
    values: dict[str, object] = {
        "strategy_version_id": "s1",
        "portfolio_ceiling": Decimal("1000"),
        "strategy_ceiling": Decimal("400"),
        "existing_exposure": Decimal("100"),
        "requested_capital": Decimal("200"),
    }
    values.update(overrides)
    return CapitalAllocationRequest(**values)  # type: ignore[arg-type]


def test_allocation_is_bounded_by_strategy_and_portfolio_capacity() -> None:
    report = AutonomousCapitalAllocator().evaluate(request(requested_capital=Decimal("500")))
    assert report.approved_allocation == Decimal("300")
    assert report.portfolio_capacity == Decimal("900")
    assert report.strategy_capacity == Decimal("300")
    assert report.can_allocate


def test_existing_exposure_is_deducted_before_allocation() -> None:
    report = AutonomousCapitalAllocator().evaluate(
        request(strategy_ceiling=Decimal("250"), existing_exposure=Decimal("200"), requested_capital=Decimal("100"))
    )
    assert report.approved_allocation == Decimal("50")


def test_portfolio_ceiling_can_be_the_tighter_boundary() -> None:
    report = AutonomousCapitalAllocator().evaluate(
        request(portfolio_ceiling=Decimal("250"), strategy_ceiling=Decimal("900"), requested_capital=Decimal("500"))
    )
    assert report.approved_allocation == Decimal("150")
    assert "allocation_bounded_by_ceiling" in report.reasons


def test_exhausted_capacity_returns_zero_safely() -> None:
    report = AutonomousCapitalAllocator().evaluate(
        request(existing_exposure=Decimal("1000"), requested_capital=Decimal("100"))
    )
    assert report.approved_allocation == Decimal("0")
    assert not report.can_allocate
    assert "portfolio_ceiling_exhausted" in report.reasons


def test_empty_strategy_identity_is_rejected() -> None:
    with pytest.raises(ValueError, match="strategy_version_id is required"):
        AutonomousCapitalAllocator().evaluate(request(strategy_version_id="  "))


@pytest.mark.parametrize(
    "field",
    ["portfolio_ceiling", "strategy_ceiling", "existing_exposure", "requested_capital"],
)
def test_negative_money_is_rejected(field: str) -> None:
    with pytest.raises(ValueError, match="cannot be negative"):
        AutonomousCapitalAllocator().evaluate(request(**{field: Decimal("-1")}))


@pytest.mark.parametrize("value", ["NaN", "Infinity", float("inf"), float("nan")])
def test_non_finite_money_is_rejected(value: object) -> None:
    with pytest.raises(ValueError, match="finite decimals"):
        AutonomousCapitalAllocator().evaluate(request(requested_capital=value))


def test_identical_inputs_are_deterministic() -> None:
    allocator = AutonomousCapitalAllocator()
    first = allocator.evaluate(request())
    second = allocator.evaluate(request())
    assert first == second
