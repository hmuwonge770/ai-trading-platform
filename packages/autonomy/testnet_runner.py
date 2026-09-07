"""Autonomous orchestration runner for controlled Binance Spot Testnet execution."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from packages.autonomy.control import AutonomousControl, AutonomousMode
from packages.autonomy.decision import Decision
from packages.autonomy.execution import AutonomousExecutionLoop, AutonomousExecutionOutcome
from packages.autonomy.recovery import AutonomousRecoveryEngine, RecoveryAction, RecoveryEvent
from packages.autonomy.risk import AutonomousRiskEngine, AutonomousRiskResult
from packages.portfolio import PortfolioSnapshot
from packages.strategies.models import MarketBar


class TestnetRunnerSubmitter(Protocol):
    def preflight(self) -> None: ...


@dataclass(frozen=True, slots=True)
class TestnetRunOutcome:
    """Result of one controlled autonomous Testnet decision cycle."""

    processed: bool
    reason: str
    risk: AutonomousRiskResult | None
    execution: AutonomousExecutionOutcome | None
    recovery_action: RecoveryAction


class AutonomousTestnetRunner:
    """Run autonomous decisions through deterministic risk and Testnet execution.

    The runner owns orchestration only. The injected execution loop remains the
    order-submission boundary, while the submitter owns Testnet endpoint and
    account-preflight controls.
    """

    def __init__(
        self,
        control: AutonomousControl,
        risk_engine: AutonomousRiskEngine,
        execution_loop: AutonomousExecutionLoop,
        submitter: TestnetRunnerSubmitter,
        recovery_engine: AutonomousRecoveryEngine | None = None,
    ) -> None:
        self.control = control
        self.risk_engine = risk_engine
        self.execution_loop = execution_loop
        self.submitter = submitter
        self.recovery_engine = recovery_engine or AutonomousRecoveryEngine()
        self._preflight_ok = False

    def preflight(self) -> None:
        """Require an explicit successful exchange/account preflight."""
        self._require_running_testnet()
        self.submitter.preflight()
        self._preflight_ok = True

    def process(
        self,
        decision: Decision,
        candle: MarketBar,
        *,
        quantity: Decimal,
        strategy_version_id: str,
        portfolio: PortfolioSnapshot,
        current_price: Decimal,
        total_exposure: Decimal,
        daily_realized_pnl: Decimal,
        liquidity_quote_volume: Decimal,
        timeframe: str,
        now: int | None = None,
    ) -> TestnetRunOutcome:
        if self.control.mode is not AutonomousMode.TESTNET:
            return self._rejected("Testnet mode is required")
        if not self.control.can_run():
            return self._rejected("autonomous control does not permit Testnet execution")
        if self.recovery_engine.state.halted:
            return self._rejected("recovery engine is halted")
        if not self._preflight_ok:
            return self._rejected("Testnet preflight is required before execution")

        risk = self.risk_engine.evaluate(
            decision,
            quantity=quantity,
            timeframe=timeframe,
            strategy_version_id=strategy_version_id,
            portfolio=portfolio,
            current_price=current_price,
            total_exposure=total_exposure,
            daily_realized_pnl=daily_realized_pnl,
            liquidity_quote_volume=liquidity_quote_volume,
            now=now,
        )
        if not risk.approved:
            return TestnetRunOutcome(False, risk.message, risk, None, RecoveryAction.CONTINUE)

        execution = self.execution_loop.process(risk, candle)
        if execution.result is None:
            return TestnetRunOutcome(False, execution.reason, risk, execution, RecoveryAction.CONTINUE)

        event = RecoveryEvent.SUCCESS if execution.result.accepted else RecoveryEvent.EXECUTION_ERROR
        recovery = self.recovery_engine.observe(event)
        if recovery.action is RecoveryAction.HALT:
            return TestnetRunOutcome(False, recovery.reason, risk, execution, recovery.action)

        return TestnetRunOutcome(
            execution.submitted and execution.result.accepted,
            execution.reason,
            risk,
            execution,
            recovery.action,
        )

    def _require_running_testnet(self) -> None:
        if self.control.mode is not AutonomousMode.TESTNET:
            raise RuntimeError("Testnet mode is required")
        if not self.control.can_run():
            raise RuntimeError("autonomous control does not permit Testnet execution")

    @staticmethod
    def _rejected(reason: str) -> TestnetRunOutcome:
        return TestnetRunOutcome(False, reason, None, None, RecoveryAction.HALT)
