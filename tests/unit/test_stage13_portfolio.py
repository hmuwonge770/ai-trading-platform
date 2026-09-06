from decimal import Decimal

import pytest

from packages.portfolio import PortfolioConfig, PortfolioEngine


def make_portfolio(cash: str = "1000") -> PortfolioEngine:
    return PortfolioEngine(
        PortfolioConfig(base_currency="usdt", initial_cash=Decimal(cash))
    )


def test_initial_cash_is_available_and_currency_is_normalized() -> None:
    portfolio = make_portfolio()

    snapshot = portfolio.snapshot()

    assert snapshot.base_currency == "USDT"
    assert snapshot.available_cash == Decimal("1000")
    assert snapshot.reserved_cash == Decimal("0")
    assert snapshot.positions == ()


def test_deposit_and_withdraw_are_recorded_as_unique_money_movements() -> None:
    portfolio = make_portfolio()

    deposit = portfolio.deposit(Decimal("250"), "funding-1")
    withdrawal = portfolio.withdraw(Decimal("100"), "withdrawal-1")

    assert deposit.movement_type == "deposit"
    assert withdrawal.movement_type == "withdrawal"
    assert portfolio.available_cash == Decimal("1150")
    assert [m.reference for m in portfolio.movements] == ["funding-1", "withdrawal-1"]

    with pytest.raises(ValueError, match="reference already exists"):
        portfolio.deposit(Decimal("1"), "funding-1")


def test_cash_reservation_cannot_exceed_available_cash() -> None:
    portfolio = make_portfolio()

    portfolio.reserve_cash(Decimal("400"))
    portfolio.release_cash(Decimal("150"))

    assert portfolio.available_cash == Decimal("750")
    assert portfolio.reserved_cash == Decimal("250")

    with pytest.raises(ValueError, match="insufficient available cash"):
        portfolio.reserve_cash(Decimal("751"))

    with pytest.raises(ValueError, match="cannot release more cash"):
        portfolio.release_cash(Decimal("251"))


def test_buy_updates_position_weighted_average_and_cash() -> None:
    portfolio = make_portfolio()

    first = portfolio.buy("btcusdt", Decimal("2"), Decimal("100"), Decimal("1"))
    second = portfolio.buy("BTCUSDT", Decimal("1"), Decimal("130"))

    assert first.quantity == Decimal("2")
    assert second.quantity == Decimal("3")
    assert second.average_entry_price == Decimal("110")
    assert portfolio.available_cash == Decimal("669")
    assert portfolio.total_fees == Decimal("1")


def test_sell_realizes_pnl_after_fee_and_keeps_remaining_cost_basis() -> None:
    portfolio = make_portfolio()
    portfolio.buy("BTCUSDT", Decimal("3"), Decimal("100"))

    position = portfolio.sell("BTCUSDT", Decimal("1"), Decimal("120"), Decimal("2"))

    assert position.quantity == Decimal("2")
    assert position.average_entry_price == Decimal("100")
    assert position.realized_pnl == Decimal("18")
    assert portfolio.realized_pnl == Decimal("18")
    assert portfolio.available_cash == Decimal("818")
    assert portfolio.total_fees == Decimal("2")


def test_selling_entire_position_resets_cost_basis() -> None:
    portfolio = make_portfolio()
    portfolio.buy("BTCUSDT", Decimal("2"), Decimal("100"))

    position = portfolio.sell("BTCUSDT", Decimal("2"), Decimal("90"))

    assert position.quantity == Decimal("0")
    assert position.average_entry_price == Decimal("0")
    assert position.realized_pnl == Decimal("-20")
    assert portfolio.available_cash == Decimal("980")


def test_insufficient_cash_and_position_are_rejected_without_mutation() -> None:
    portfolio = make_portfolio("100")

    with pytest.raises(ValueError, match="insufficient available cash"):
        portfolio.buy("BTCUSDT", Decimal("2"), Decimal("60"))

    assert portfolio.available_cash == Decimal("100")
    assert portfolio.snapshot().positions == ()

    with pytest.raises(ValueError, match="insufficient position"):
        portfolio.sell("BTCUSDT", Decimal("1"), Decimal("100"))

    assert portfolio.available_cash == Decimal("100")


def test_trade_inputs_are_validated() -> None:
    portfolio = make_portfolio()

    with pytest.raises(ValueError, match="quantity"):
        portfolio.buy("BTCUSDT", Decimal("0"), Decimal("100"))
    with pytest.raises(ValueError, match="price"):
        portfolio.buy("BTCUSDT", Decimal("1"), Decimal("0"))
    with pytest.raises(ValueError, match="fee"):
        portfolio.buy("BTCUSDT", Decimal("1"), Decimal("100"), Decimal("-1"))
