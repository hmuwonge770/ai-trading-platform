from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from packages.autonomy.decision import Decision, DecisionAction
from packages.autonomy.execution import AutonomousExecutionLoop
from packages.autonomy.risk import AutonomousRiskResult
from packages.execution.service import ExecutionResult
from packages.risk.gateway import RiskDecision, RiskReason
from packages.strategies.models import MarketBar, Signal
from packages.trading.paper import OrderIntent


class FakeSubmitter:
    def __init__(self) -> None:
        self.calls = 0

    def submit(self, order, risk_decision, candle):
        self.calls += 1
        return ExecutionResult(True, "simulated execution accepted", None, None)


def candle(symbol: str = "BTCUSDT", timeframe: str = "1m") -> MarketBar:
    return MarketBar(
        symbol=symbol,
        timeframe=timeframe,
        open_time=datetime(2026, 9, 7, tzinfo=timezone.utc),
        open=Decimal("100"),
        high=Decimal("101"),
        low=Decimal("99"),
        close=Decimal("100"),
        volume=Decimal("1000"),
    )


def approved_result() -> AutonomousRiskResult:
    decision = Decision(
        DecisionAction.BUY,
        "BTCUSDT",
        Decimal("0.90"),
        "validated autonomous signal",
        1_000,
    )
    order = OrderIntent(
        intent_id=uuid4(),
        signal_id=uuid4(),
        strategy_version_id="strategy-v1",
        symbol="BTCUSDT",
        timeframe="1m",
        side=Signal.BUY,
        quantity=Decimal("1"),
        reference_price=Decimal("100"),
        client_order_id="auto-test-1",
        reason="validated autonomous signal",
    )
    risk = RiskDecision(
        approved=True,
        reason=RiskReason.APPROVED,
        message="approved",
        order_id=order.client_order_id,
        order_notional=Decimal("100"),
        projected_position_notional=Decimal("100"),
        projected_total_exposure=Decimal("100"),
    )
    return AutonomousRiskResult(True, "approved", "approved", decision, order, risk)


def test_only_risk_approved_order_is_submitted() -> None:
    submitter = FakeSubmitter()
    loop = AutonomousExecutionLoop(submitter)

    result = loop.process(approved_result(), candle())

    assert result.submitted is True
    assert submitter.calls == 1


def test_duplicate_order_is_suppressed() -> None:
    submitter = FakeSubmitter()
    loop = AutonomousExecutionLoop(submitter)
    risk_result = approved_result()

    first = loop.process(risk_result, candle())
    second = loop.process(risk_result, candle())

    assert first.submitted is True
    assert second.submitted is False
    assert "duplicate" in second.reason
    assert submitter.calls == 1


def test_unapproved_risk_result_never_reaches_submitter() -> None:
    submitter = FakeSubmitter()
    loop = AutonomousExecutionLoop(submitter)
    risk_result = approved_result()
    risk_result = AutonomousRiskResult(
        False,
        "gateway_rejected",
        "rejected",
        risk_result.decision,
        None,
        None,
    )

    result = loop.process(risk_result, candle())

    assert result.submitted is False
    assert submitter.calls == 0


def test_symbol_mismatch_is_rejected_before_submitter() -> None:
    submitter = FakeSubmitter()
    loop = AutonomousExecutionLoop(submitter)

    result = loop.process(approved_result(), candle(symbol="ETHUSDT"))

    assert result.submitted is False
    assert "symbol" in result.reason
    assert submitter.calls == 0


def test_timeframe_mismatch_is_rejected_before_submitter() -> None:
    submitter = FakeSubmitter()
    loop = AutonomousExecutionLoop(submitter)

    result = loop.process(approved_result(), candle(timeframe="5m"))

    assert result.submitted is False
    assert "timeframe" in result.reason
    assert submitter.calls == 0


def test_invalid_dedupe_capacity_is_rejected() -> None:
    submitter = FakeSubmitter()

    try:
        AutonomousExecutionLoop(submitter, dedupe_capacity=0)
    except ValueError as exc:
        assert "dedupe_capacity" in str(exc)
    else:
        raise AssertionError("expected invalid dedupe capacity to fail")
