"""Paper-only autonomous orchestration across control, risk, execution, and recovery."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from packages.autonomy.control import AutonomousControl, AutonomousMode
from packages.autonomy.decision import Decision
from packages.autonomy.execution import AutonomousExecutionLoop, AutonomousExecutionOutcome
from packages.autonomy.recovery import AutonomousRecoveryEngine, RecoveryAction, RecoveryEvent
from packages.autonomy.risk import AutonomousRiskEngine, AutonomousRiskResult
from packages.portfolio import PortfolioSnapshot
from packages.strategies.models import MarketBar


@dataclass(frozen=True, slots=True)
class PaperRunOutcome:
    processed: bool
    reason: str
    risk: AutonomousRiskResult | None
    execution: AutonomousExecutionOutcome | None
    recovery_action: RecoveryAction


class AutonomousPaperRunner:
    """Run autonomous decisions only when the control plane is explicitly PAPER."""

    def __init__(
        self,
        control: AutonomousControl,
        risk_engine: AutonomousRiskEngine,
        execution_loop: AutonomousExecutionLoop,
        recovery_engine: AutonomousRecoveryEngine | None = None,
    ) -> None:
        self.control = control
        self.risk_engine = risk_engine
        self.execution_loop = execution_loop
        self.recovery_engine = recovery_engine or AutonomousRecoveryEngine()

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
    ) -> PaperRunOutcome:
        if self.control.mode is not AutonomousMode.PAPER:
            return PaperRunOutcome(False, "paper mode is required", None, None, RecoveryAction.HALT)
        if not self.control.can_run():
            return PaperRunOutcome(False, "autonomous control does not permit execution", None, None, RecoveryAction.HALT)
        if self.recovery_engine.state.halted:
            return PaperRunOutcome(False, "recovery engine is halted", None, None, RecoveryAction.HALT)

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
            return PaperRunOutcome(False, risk.message, risk, None, RecoveryAction.CONTINUE)

        execution = self.execution_loop.process(risk, candle)
        if execution.result is None:
            return PaperRunOutcome(False, execution.reason, risk, execution, RecoveryAction.CONTINUE)

        recovery = self.recovery_engine.observe(
            RecoveryEvent.SUCCESS if execution.result.accepted else RecoveryEvent.EXECUTION_ERROR,
        )
        if recovery.action is RecoveryAction.HALT:
            return PaperRunOutcome(False, recovery.reason, risk, execution, recovery.action)
        return PaperRunOutcome(execution.submitted and execution.result.accepted, execution.reason, risk, execution, recovery.action)
