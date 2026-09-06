from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from packages.execution.service import ExecutionService
from packages.execution.simulator import ExecutionConfig, ExecutionSimulator, ExecutionStatus
from packages.risk import RiskDecision, RiskReason
from packages.strategies.models import MarketBar, Signal
from packages.trading.paper import OrderIntent


def make_order() -> OrderIntent:
    signal_id = uuid4()
    return OrderIntent(
        intent_id=uuid4(), signal_id=signal_id, strategy_version_id="strategy-v1",
        symbol="BTCUSDT", timeframe="1m", side=Signal.BUY, quantity=Decimal("1"),
        reference_price=Decimal("100"), client_order_id=f"paper-{signal_id.hex}", reason="test",
    )


def make_candle() -> MarketBar:
    return MarketBar(
        symbol="BTCUSDT", timeframe="1m", open_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
        open=Decimal("100"), high=Decimal("101"), low=Decimal("99"), close=Decimal("100"), volume=Decimal("10"),
    )


def approved(order: OrderIntent) -> RiskDecision:
    return RiskDecision(
        approved=True, reason=RiskReason.APPROVED,
        message="approved", order_id=order.client_order_id,
        order_notional=Decimal("100"), projected_position_notional=Decimal("100"),
        projected_total_exposure=Decimal("100"),
    )


def test_service_requires_risk_approval_before_backend() -> None:
    service = ExecutionService(ExecutionSimulator())
    order = make_order()
    decision = RiskDecision(
        approved=False, reason=RiskReason.DAILY_LOSS_LIMIT,
        message="blocked", order_id=order.client_order_id,
        order_notional=Decimal("100"), projected_position_notional=Decimal("100"),
        projected_total_exposure=Decimal("100"),
    )

    result = service.submit(order, decision, make_candle())

    assert result.accepted is False
    assert result.simulated_order is None
    assert result.fill is None


def test_service_rejects_mismatched_risk_decision() -> None:
    service = ExecutionService(ExecutionSimulator())
    order = make_order()
    other = make_order()

    result = service.submit(order, approved(other), make_candle())

    assert result.accepted is False
    assert result.simulated_order is None


def test_service_delegates_approved_order_to_injected_backend() -> None:
    service = ExecutionService(ExecutionSimulator(ExecutionConfig(slippage_rate=Decimal("0.01"))))
    order = make_order()

    result = service.submit(order, approved(order), make_candle())

    assert result.accepted is True
    assert result.simulated_order is not None
    assert result.simulated_order.status == ExecutionStatus.FILLED
    assert result.fill is not None
    assert result.fill.price == Decimal("101")


def test_service_is_idempotent_by_client_order_id() -> None:
    service = ExecutionService(ExecutionSimulator())
    order = make_order()
    first = service.submit(order, approved(order), make_candle())
    second = service.submit(order, approved(order), make_candle())

    assert second is first
    assert second.simulated_order is first.simulated_order
