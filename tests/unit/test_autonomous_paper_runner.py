from types import SimpleNamespace
from decimal import Decimal

from packages.autonomy.control import AutonomousControl, AutonomousMode, AutonomousState
from packages.autonomy.paper_runner import AutonomousPaperRunner
from packages.autonomy.recovery import AutonomousRecoveryEngine, RecoveryAction
from packages.autonomy.risk import AutonomousRiskResult
from packages.autonomy.execution import AutonomousExecutionOutcome


class FakeRisk:
    def __init__(self, approved: bool) -> None:
        self.approved = approved

    def evaluate(self, decision, **kwargs):
        return AutonomousRiskResult(
            self.approved,
            "approved" if self.approved else "rejected",
            "ok" if self.approved else "risk rejected",
            decision,
            SimpleNamespace(client_order_id="auto-1") if self.approved else None,
            SimpleNamespace(approved=True) if self.approved else None,
        )


class FakeExecution:
    def __init__(self, accepted: bool) -> None:
        self.accepted = accepted

    def process(self, risk, candle):
        result = SimpleNamespace(accepted=self.accepted, reason="paper fill" if self.accepted else "paper rejected")
        return AutonomousExecutionOutcome(True, result.reason, result)


def running_paper_control() -> AutonomousControl:
    return AutonomousControl(
        mode=AutonomousMode.PAPER,
        state=AutonomousState.RUNNING,
        trading_enabled=True,
        kill_switch_enabled=False,
        circuit_breaker_open=False,
    )


def test_non_paper_mode_is_rejected() -> None:
    control = running_paper_control().with_mode(AutonomousMode.TESTNET)
    runner = AutonomousPaperRunner(control, FakeRisk(True), FakeExecution(True))
    result = runner.process(
        SimpleNamespace(),
        SimpleNamespace(),
        quantity=Decimal("1"),
        strategy_version_id="v1",
        portfolio=SimpleNamespace(),
        current_price=Decimal("100"),
        total_exposure=Decimal("0"),
        daily_realized_pnl=Decimal("0"),
        liquidity_quote_volume=Decimal("10000"),
        timeframe="1m",
    )
    assert not result.processed
    assert result.recovery_action is RecoveryAction.HALT


def test_control_must_be_running() -> None:
    control = AutonomousControl(mode=AutonomousMode.PAPER, trading_enabled=True)
    runner = AutonomousPaperRunner(control, FakeRisk(True), FakeExecution(True))
    result = runner.process(
        SimpleNamespace(), SimpleNamespace(), quantity=Decimal("1"), strategy_version_id="v1",
        portfolio=SimpleNamespace(), current_price=Decimal("100"), total_exposure=Decimal("0"),
        daily_realized_pnl=Decimal("0"), liquidity_quote_volume=Decimal("10000"), timeframe="1m",
    )
    assert not result.processed


def test_approved_paper_order_is_processed() -> None:
    runner = AutonomousPaperRunner(
        running_paper_control(), FakeRisk(True), FakeExecution(True), AutonomousRecoveryEngine()
    )
    result = runner.process(
        SimpleNamespace(), SimpleNamespace(), quantity=Decimal("1"), strategy_version_id="v1",
        portfolio=SimpleNamespace(), current_price=Decimal("100"), total_exposure=Decimal("0"),
        daily_realized_pnl=Decimal("0"), liquidity_quote_volume=Decimal("10000"), timeframe="1m",
    )
    assert result.processed
    assert result.recovery_action is RecoveryAction.CONTINUE


def test_risk_rejection_does_not_execute() -> None:
    runner = AutonomousPaperRunner(running_paper_control(), FakeRisk(False), FakeExecution(True))
    result = runner.process(
        SimpleNamespace(), SimpleNamespace(), quantity=Decimal("1"), strategy_version_id="v1",
        portfolio=SimpleNamespace(), current_price=Decimal("100"), total_exposure=Decimal("0"),
        daily_realized_pnl=Decimal("0"), liquidity_quote_volume=Decimal("10000"), timeframe="1m",
    )
    assert not result.processed
    assert result.execution is None
