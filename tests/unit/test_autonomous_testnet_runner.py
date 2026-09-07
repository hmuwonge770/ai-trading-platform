from types import SimpleNamespace
from decimal import Decimal

from packages.autonomy.control import AutonomousControl, AutonomousMode, AutonomousState
from packages.autonomy.execution import AutonomousExecutionOutcome
from packages.autonomy.recovery import AutonomousRecoveryEngine, RecoveryAction
from packages.autonomy.risk import AutonomousRiskResult
from packages.autonomy.testnet_runner import AutonomousTestnetRunner


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
        result = SimpleNamespace(accepted=self.accepted, reason="testnet fill" if self.accepted else "testnet rejected")
        return AutonomousExecutionOutcome(True, result.reason, result)


class FakeSubmitter:
    def __init__(self) -> None:
        self.preflight_calls = 0

    def preflight(self) -> None:
        self.preflight_calls += 1


def running_testnet_control() -> AutonomousControl:
    return AutonomousControl(
        mode=AutonomousMode.TESTNET,
        state=AutonomousState.RUNNING,
        trading_enabled=True,
        kill_switch_enabled=False,
        circuit_breaker_open=False,
    )


def run(runner: AutonomousTestnetRunner):
    return runner.process(
        SimpleNamespace(), SimpleNamespace(), quantity=Decimal("1"), strategy_version_id="v1",
        portfolio=SimpleNamespace(), current_price=Decimal("100"), total_exposure=Decimal("0"),
        daily_realized_pnl=Decimal("0"), liquidity_quote_volume=Decimal("10000"), timeframe="1m",
    )


def test_preflight_is_required_before_execution() -> None:
    submitter = FakeSubmitter()
    runner = AutonomousTestnetRunner(running_testnet_control(), FakeRisk(True), FakeExecution(True), submitter)
    result = run(runner)
    assert not result.processed
    assert "preflight" in result.reason
    assert submitter.preflight_calls == 0


def test_preflight_delegates_to_testnet_submitter() -> None:
    submitter = FakeSubmitter()
    runner = AutonomousTestnetRunner(running_testnet_control(), FakeRisk(True), FakeExecution(True), submitter)
    runner.preflight()
    assert submitter.preflight_calls == 1
    assert run(runner).processed


def test_only_testnet_mode_is_allowed() -> None:
    submitter = FakeSubmitter()
    control = running_testnet_control().with_mode(AutonomousMode.PAPER)
    runner = AutonomousTestnetRunner(control, FakeRisk(True), FakeExecution(True), submitter)
    result = run(runner)
    assert not result.processed
    assert result.recovery_action is RecoveryAction.HALT


def test_risk_rejection_does_not_execute() -> None:
    submitter = FakeSubmitter()
    runner = AutonomousTestnetRunner(running_testnet_control(), FakeRisk(False), FakeExecution(True), submitter)
    runner.preflight()
    result = run(runner)
    assert not result.processed
    assert result.execution is None


def test_execution_result_is_observed_by_recovery() -> None:
    submitter = FakeSubmitter()
    runner = AutonomousTestnetRunner(
        running_testnet_control(), FakeRisk(True), FakeExecution(True), submitter, AutonomousRecoveryEngine()
    )
    runner.preflight()
    result = run(runner)
    assert result.processed
    assert result.recovery_action is RecoveryAction.CONTINUE
