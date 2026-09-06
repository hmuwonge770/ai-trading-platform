from datetime import datetime, timezone
from decimal import Decimal

import pytest

from packages.execution import ExecutionConfig, ExecutionSimulator, ExecutionStatus
from packages.strategies.models import MarketBar, Signal
from packages.trading.paper import OrderIntent
from uuid import uuid4


def make_order(side: Signal, quantity: str = "2") -> OrderIntent:
    signal_id = uuid4()
    return OrderIntent(
        intent_id=uuid4(), signal_id=signal_id, strategy_version_id="strategy-v1",
        symbol="BTCUSDT", timeframe="1m", side=side, quantity=Decimal(quantity),
        reference_price=Decimal("99"), client_order_id=f"paper-{signal_id.hex}", reason="test",
    )


def make_candle(volume: str = "10", open_price: str = "100") -> MarketBar:
    return MarketBar(
        symbol="BTCUSDT", timeframe="1m", open_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
        open=Decimal(open_price), high=Decimal("101"), low=Decimal("99"), close=Decimal("100"),
        volume=Decimal(volume),
    )


def test_full_fill_uses_next_candle_open_and_buy_slippage() -> None:
    result, fill = ExecutionSimulator(ExecutionConfig(slippage_rate=Decimal("0.01"))).execute(
        make_order(Signal.BUY), make_candle()
    )

    assert result.status == ExecutionStatus.FILLED
    assert result.filled_quantity == Decimal("2")
    assert result.remaining_quantity == Decimal("0")
    assert result.average_fill_price == Decimal("101")
    assert fill is not None
    assert fill.price == Decimal("101")
    assert fill.quantity == Decimal("2")


def test_sell_slippage_works_in_the_opposite_direction() -> None:
    result, fill = ExecutionSimulator(ExecutionConfig(slippage_rate=Decimal("0.02"))).execute(
        make_order(Signal.SELL), make_candle()
    )

    assert result.status == ExecutionStatus.FILLED
    assert fill is not None
    assert fill.price == Decimal("98")


def test_partial_fill_reports_remaining_quantity() -> None:
    result, fill = ExecutionSimulator(ExecutionConfig(fill_ratio=Decimal("0.25"))).execute(
        make_order(Signal.BUY, "4"), make_candle()
    )

    assert result.status == ExecutionStatus.PARTIALLY_FILLED
    assert result.filled_quantity == Decimal("1.00")
    assert result.remaining_quantity == Decimal("3.00")
    assert fill is not None
    assert fill.quantity == Decimal("1.00")


def test_zero_volume_can_reject_without_creating_a_fill() -> None:
    result, fill = ExecutionSimulator().execute(make_order(Signal.BUY), make_candle("0"))

    assert result.status == ExecutionStatus.REJECTED
    assert result.filled_quantity == Decimal("0")
    assert result.remaining_quantity == Decimal("2")
    assert fill is None


def test_symbol_mismatch_is_rejected_before_simulation() -> None:
    with pytest.raises(ValueError, match="symbol"):
        ExecutionSimulator().execute(make_order(Signal.BUY), make_candle()) if False else ExecutionSimulator().execute(
            OrderIntent(
                intent_id=uuid4(), signal_id=uuid4(), strategy_version_id="strategy-v1",
                symbol="ETHUSDT", timeframe="1m", side=Signal.BUY, quantity=Decimal("1"),
                reference_price=Decimal("100"), client_order_id="paper-test", reason="test",
            ),
            make_candle(),
        )


def test_invalid_execution_config_is_rejected() -> None:
    with pytest.raises(ValueError, match="fill_ratio"):
        ExecutionConfig(fill_ratio=Decimal("0"))
    with pytest.raises(ValueError, match="slippage_rate"):
        ExecutionConfig(slippage_rate=Decimal("1"))
