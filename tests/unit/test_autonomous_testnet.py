from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from packages.autonomy.control import AutonomousControl, AutonomousMode, AutonomousState
from packages.autonomy.testnet import BinanceTestnetExecutionSubmitter
from packages.execution.service import ExecutionResult
from packages.execution.simulator import ExecutionStatus, SimulatedOrder
from packages.risk.gateway import RiskDecision, RiskReason
from packages.strategies.models import MarketBar, Signal
from packages.trading.paper import OrderIntent


class FakeTestnet:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.pings = 0
        self.accounts = 0
        self.executions = 0

    def ping(self) -> None:
        self.pings += 1

    def get_account(self) -> dict[str, object]:
        self.accounts += 1
        return {"accountType": "SPOT"}

    def execute(self, order, candle):
        self.executions += 1
        if self.fail:
            raise RuntimeError("temporary exchange failure")
        simulated = SimulatedOrder(
            simulation_id=uuid4(),
            order_id=order.client_order_id,
            status=ExecutionStatus.FILLED,
            requested_quantity=order.quantity,
            filled_quantity=order.quantity,
            remaining_quantity=Decimal("0"),
            average_fill_price=order.reference_price,
            reason="Binance Spot Testnet order accepted",
        )
        return simulated, None


def running_testnet_control() -> AutonomousControl:
    control = AutonomousControl().with_mode(AutonomousMode.TESTNET).with_trading(True)
    control = control.with_kill_switch(False)
    return AutonomousControl(
        mode=AutonomousMode.TESTNET,
        state=AutonomousState.RUNNING,
        trading_enabled=True,
        kill_switch_enabled=False,
        circuit_breaker_open=False,
    )


def candle() -> MarketBar:
    return MarketBar(
        symbol="BTCUSDT",
        timeframe="1m",
        open_time=datetime(2026, 9, 7, tzinfo=timezone.utc),
        open=Decimal("100"),
        high=Decimal("101"),
        low=Decimal("99"),
        close=Decimal("100"),
        volume=Decimal("1000"),
    )


def order() -> OrderIntent:
    return OrderIntent(
        intent_id=uuid4(),
        signal_id=uuid4(),
        strategy_version_id="strategy-v1",
        symbol="BTCUSDT",
        timeframe="1m",
        side=Signal.BUY,
        quantity=Decimal("1"),
        reference_price=Decimal("100"),
        client_order_id="auto-testnet-1",
        reason="validated autonomous signal",
    )


def approved_risk(item: OrderIntent) -> RiskDecision:
    return RiskDecision(
        approved=True,
        reason=RiskReason.APPROVED,
        message="approved",
        order_id=item.client_order_id,
        order_notional=Decimal("100"),
        projected_position_notional=Decimal("100"),
        projected_total_exposure=Decimal("100"),
    )


def test_preflight_is_required_before_submission() -> None:
    exchange = FakeTestnet()
    submitter = BinanceTestnetExecutionSubmitter(running_testnet_control(), exchange)
    item = order()

    result = submitter.submit(item, approved_risk(item), candle())

    assert result.accepted is False
    assert "preflight" in result.reason
    assert exchange.executions == 0


def test_preflight_then_approved_order_reaches_testnet() -> None:
    exchange = FakeTestnet()
    submitter = BinanceTestnetExecutionSubmitter(running_testnet_control(), exchange)
    submitter.preflight()
    item = order()

    result = submitter.submit(item, approved_risk(item), candle())

    assert result.accepted is True
    assert exchange.pings == 1
    assert exchange.accounts == 1
    assert exchange.executions == 1


def test_non_testnet_mode_is_rejected() -> None:
    exchange = FakeTestnet()
    control = running_testnet_control().with_mode(AutonomousMode.PAPER)
    submitter = BinanceTestnetExecutionSubmitter(control, exchange)

    result = submitter.submit(order(), approved_risk(order()), candle())

    assert result.accepted is False
    assert "Testnet mode" in result.reason
    assert exchange.executions == 0


def test_kill_switch_and_circuit_breaker_block_submission() -> None:
    exchange = FakeTestnet()
    control = running_testnet_control().with_kill_switch(True)
    submitter = BinanceTestnetExecutionSubmitter(control, exchange)
    item = order()

    result = submitter.submit(item, approved_risk(item), candle())

    assert result.accepted is False
    assert "control" in result.reason
    assert exchange.executions == 0


def test_risk_identity_mismatch_is_rejected() -> None:
    exchange = FakeTestnet()
    submitter = BinanceTestnetExecutionSubmitter(running_testnet_control(), exchange)
    submitter.preflight()
    item = order()
    decision = approved_risk(item)
    other = order()

    result = submitter.submit(other, decision, candle())

    assert result.accepted is False
    assert "risk decision" in result.reason
    assert exchange.executions == 0


def test_exchange_failure_is_not_reported_as_success() -> None:
    exchange = FakeTestnet(fail=True)
    submitter = BinanceTestnetExecutionSubmitter(running_testnet_control(), exchange)
    submitter.preflight()
    item = order()

    result = submitter.submit(item, approved_risk(item), candle())

    assert isinstance(result, ExecutionResult)
    assert result.accepted is False
    assert "execution failed" in result.reason
    assert exchange.executions == 1
