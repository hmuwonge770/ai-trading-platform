from decimal import Decimal
from uuid import uuid4

import pytest

from packages.portfolio import PortfolioConfig, PortfolioEngine
from packages.risk import RiskContext, RiskGateway, RiskLimits, RiskReason
from packages.strategies.models import Signal
from packages.trading.paper import OrderIntent


def order(side: Signal, quantity: str = "1", price: str = "100") -> OrderIntent:
    signal_id = uuid4()
    return OrderIntent(
        intent_id=uuid4(),
        signal_id=signal_id,
        strategy_version_id="strategy-v1",
        symbol="BTCUSDT",
        timeframe="1m",
        side=side,
        quantity=Decimal(quantity),
        reference_price=Decimal(price),
        client_order_id=f"paper-{signal_id.hex}",
        reason="test",
    )


def context(cash: str = "1000", exposure: str = "0", daily_pnl: str = "0") -> RiskContext:
    portfolio = PortfolioEngine(
        PortfolioConfig(base_currency="USDT", initial_cash=Decimal(cash))
    ).snapshot()
    return RiskContext(
        portfolio=portfolio,
        current_price=Decimal("100"),
        total_exposure=Decimal(exposure),
        daily_realized_pnl=Decimal(daily_pnl),
    )


def limits() -> RiskLimits:
    return RiskLimits(
        max_order_notional=Decimal("250"),
        max_position_notional=Decimal("500"),
        max_total_exposure=Decimal("1000"),
        max_daily_loss=Decimal("100"),
        min_cash_after_order=Decimal("100"),
    )


def test_approved_order_is_deterministic() -> None:
    gateway = RiskGateway(limits())
    decision = gateway.evaluate(order(Signal.BUY, "2"), context())

    assert decision.approved is True
    assert decision.reason == RiskReason.APPROVED
    assert decision.order_notional == Decimal("200")
    assert decision.projected_position_notional == Decimal("200")
    assert decision.projected_total_exposure == Decimal("200")


def test_order_notional_limit_rejects_large_order() -> None:
    decision = RiskGateway(limits()).evaluate(order(Signal.BUY, "3"), context())

    assert decision.approved is False
    assert decision.reason == RiskReason.ORDER_NOTIONAL_LIMIT


def test_projected_position_limit_rejects_additional_position() -> None:
    decision = RiskGateway(limits()).evaluate(order(Signal.BUY, "2"), context(exposure="400"))

    assert decision.approved is True

    position_portfolio = PortfolioEngine(
        PortfolioConfig(base_currency="USDT", initial_cash=Decimal("1000"))
    )
    position_portfolio.buy("BTCUSDT", Decimal("4"), Decimal("100"))
    risk_context = RiskContext(
        portfolio=position_portfolio.snapshot(),
        current_price=Decimal("100"),
        total_exposure=Decimal("400"),
        daily_realized_pnl=Decimal("0"),
    )
    rejected = RiskGateway(limits()).evaluate(order(Signal.BUY, "2"), risk_context)

    assert rejected.approved is False
    assert rejected.reason == RiskReason.POSITION_NOTIONAL_LIMIT


def test_total_exposure_limit_rejects_new_risk() -> None:
    decision = RiskGateway(limits()).evaluate(order(Signal.BUY, "2"), context(exposure="900"))

    assert decision.approved is False
    assert decision.reason == RiskReason.TOTAL_EXPOSURE_LIMIT


def test_minimum_cash_rule_rejects_purchase() -> None:
    decision = RiskGateway(limits()).evaluate(order(Signal.BUY, "9"), context(cash="1000"))

    assert decision.approved is False
    assert decision.reason == RiskReason.INSUFFICIENT_CASH


def test_daily_loss_limit_blocks_new_buys_but_allows_risk_reducing_sell() -> None:
    gateway = RiskGateway(limits())
    buy = gateway.evaluate(order(Signal.BUY, "1"), context(daily_pnl="-100"))
    assert buy.approved is False
    assert buy.reason == RiskReason.DAILY_LOSS_LIMIT

    portfolio = PortfolioEngine(PortfolioConfig(base_currency="USDT", initial_cash=Decimal("0")))
    portfolio.deposit(Decimal("1000"), "funding")
    portfolio.buy("BTCUSDT", Decimal("2"), Decimal("100"))
    sell_context = RiskContext(
        portfolio=portfolio.snapshot(),
        current_price=Decimal("100"),
        total_exposure=Decimal("200"),
        daily_realized_pnl=Decimal("-100"),
    )
    sell = gateway.evaluate(order(Signal.SELL, "1"), sell_context)
    assert sell.approved is True


def test_sell_cannot_exceed_position() -> None:
    decision = RiskGateway(limits()).evaluate(order(Signal.SELL, "1"), context())

    assert decision.approved is False
    assert decision.reason == RiskReason.INSUFFICIENT_POSITION


def test_hold_is_never_an_order() -> None:
    decision = RiskGateway(limits()).evaluate(order(Signal.HOLD), context())

    assert decision.approved is False
    assert decision.reason == RiskReason.INVALID_ORDER


def test_invalid_limits_are_rejected() -> None:
    with pytest.raises(ValueError, match="max_order_notional"):
        RiskLimits(
            max_order_notional=Decimal("0"),
            max_position_notional=Decimal("1"),
            max_total_exposure=Decimal("1"),
            max_daily_loss=Decimal("1"),
        )
