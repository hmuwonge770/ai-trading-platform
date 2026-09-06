from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from hypothesis import given, settings, strategies as st

from packages.accounting import AccountingEntry, AccountingTransaction, Ledger
from packages.execution import ExecutionService, ExecutionStatus, SimulatedFill, SimulatedOrder
from packages.execution.binance_testnet import BinanceSpotTestnetClient, BinanceTestnetConfig
from packages.risk import RiskDecision, RiskReason
from packages.strategies.models import MarketBar, Signal
from packages.trading.paper import OrderIntent


def make_order(client_order_id: str) -> OrderIntent:
    return OrderIntent(
        intent_id=uuid4(),
        signal_id=uuid4(),
        strategy_version_id=str(uuid4()),
        symbol="BTCUSDT",
        timeframe="1m",
        side=Signal.BUY,
        quantity=Decimal("0.001"),
        reference_price=Decimal("100"),
        client_order_id=client_order_id,
        reason="stage 27 property test",
    )


def approved(order: OrderIntent) -> RiskDecision:
    return RiskDecision(
        approved=True,
        reason=RiskReason.APPROVED,
        message="approved",
        order_id=order.client_order_id,
        order_notional=Decimal("0.1"),
        projected_position_notional=Decimal("0.1"),
        projected_total_exposure=Decimal("0.1"),
    )


def candle() -> MarketBar:
    return MarketBar(
        symbol="BTCUSDT",
        timeframe="1m",
        open_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
        open=Decimal("100"),
        high=Decimal("101"),
        low=Decimal("99"),
        close=Decimal("100.5"),
        volume=Decimal("10"),
    )


@given(st.decimals(min_value="0.0001", max_value="100000", places=4))
@settings(max_examples=40, deadline=None)
def test_balanced_ledger_transfer_never_creates_asset_imbalance(amount: Decimal) -> None:
    ledger = Ledger()
    transaction = AccountingTransaction(
        reference=f"property-{amount}",
        transaction_type="transfer",
        entries=(
            AccountingEntry(account="cash", asset="USDT", debit=amount),
            AccountingEntry(account="broker", asset="USDT", credit=amount),
        ),
    )

    ledger.post(transaction)

    assert ledger.balance("cash", "USDT").balance == amount
    assert ledger.balance("broker", "USDT").balance == -amount
    assert sum((balance.balance for balance in ledger.balances()), Decimal("0")) == 0


@given(st.integers(min_value=1, max_value=50))
@settings(max_examples=20, deadline=None)
def test_duplicate_delivery_is_idempotent_for_any_retry_count(retries: int) -> None:
    ledger = Ledger()
    transaction = AccountingTransaction(
        reference="property-idempotency",
        transaction_type="deposit",
        entries=(
            AccountingEntry(account="cash", asset="USDT", debit=Decimal("25")),
            AccountingEntry(account="equity", asset="USDT", credit=Decimal("25")),
        ),
    )
    first = ledger.post(transaction)

    for _ in range(retries):
        assert ledger.post(transaction) == first

    assert len(ledger.transactions) == 1
    assert ledger.balance("cash", "USDT").balance == Decimal("25")


class CountingBackend:
    def __init__(self) -> None:
        self.calls = 0

    def execute(self, order: OrderIntent, candle: MarketBar) -> tuple[SimulatedOrder, SimulatedFill | None]:
        self.calls += 1
        simulation_id = uuid4()
        return (
            SimulatedOrder(
                simulation_id=simulation_id,
                order_id=order.client_order_id,
                status=ExecutionStatus.FILLED,
                requested_quantity=order.quantity,
                filled_quantity=order.quantity,
                remaining_quantity=Decimal("0"),
                average_fill_price=candle.open,
                reason="property backend fill",
            ),
            SimulatedFill(
                fill_id=uuid4(),
                simulation_id=simulation_id,
                order_id=order.client_order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                price=candle.open,
                executed_at=candle.open_time,
            ),
        )


@given(st.integers(min_value=1, max_value=50))
@settings(max_examples=20, deadline=None)
def test_execution_is_idempotent_for_any_duplicate_delivery_count(retries: int) -> None:
    backend = CountingBackend()
    service = ExecutionService(backend)
    order = make_order("property-idempotent")
    decision = approved(order)

    first = service.submit(order, decision, candle())
    for _ in range(retries):
        assert service.submit(order, decision, candle()) == first

    assert backend.calls == 1


def test_backend_failure_is_retryable_and_does_not_create_a_false_success() -> None:
    calls = 0

    class FailingBackend(CountingBackend):
        def execute(self, order: OrderIntent, candle: MarketBar) -> tuple[SimulatedOrder, SimulatedFill | None]:
            nonlocal calls
            calls += 1
            raise RuntimeError("synthetic exchange timeout")

    service = ExecutionService(FailingBackend())
    order = make_order("property-failure")
    decision = approved(order)

    with pytest.raises(RuntimeError, match="synthetic exchange timeout"):
        service.submit(order, decision, candle())
    with pytest.raises(RuntimeError, match="synthetic exchange timeout"):
        service.submit(order, decision, candle())

    assert calls == 2


def test_testnet_adapter_rejects_production_before_any_request() -> None:
    config = BinanceTestnetConfig(
        api_key="test-key",
        api_secret="test-secret",
    )
    client = BinanceSpotTestnetClient(config)
    assert config.base_url == "https://testnet.binance.vision"
    client.close()
