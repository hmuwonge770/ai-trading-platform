"""Controlled Binance Spot Testnet execution boundary for autonomous trading."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from packages.autonomy.control import AutonomousControl, AutonomousMode
from packages.execution.binance_testnet import BinanceSpotTestnetClient
from packages.execution.service import ExecutionResult
from packages.risk import RiskDecision, RiskReason
from packages.strategies.models import MarketBar
from packages.trading.paper import OrderIntent


class TestnetExecutionTransport(Protocol):
    def execute(self, order: OrderIntent, candle: MarketBar): ...


@dataclass(frozen=True, slots=True)
class TestnetExecutionPolicy:
    """Explicit gates required before an autonomous Testnet order is sent."""

    require_account_preflight: bool = True


class BinanceTestnetExecutionSubmitter:
    """Adapt the Binance Spot Testnet client to the autonomous execution boundary.

    This class is deliberately incapable of targeting Binance production: the
    underlying client is already hard-wired to the Spot Testnet endpoint. The
    control plane must additionally be explicitly RUNNING in TESTNET mode with
    trading enabled, the kill switch off, and the circuit breaker closed.
    """

    def __init__(
        self,
        control: AutonomousControl,
        client: BinanceSpotTestnetClient,
        *,
        policy: TestnetExecutionPolicy | None = None,
    ) -> None:
        self.control = control
        self.client = client
        self.policy = policy or TestnetExecutionPolicy()
        self._preflight_ok = False

    def preflight(self) -> None:
        """Verify the configured Testnet account before autonomous execution."""
        self._require_testnet_control()
        self.client.ping()
        if self.policy.require_account_preflight:
            self.client.get_account()
        self._preflight_ok = True

    def submit(
        self,
        order: OrderIntent,
        risk_decision: RiskDecision,
        candle: MarketBar,
    ) -> ExecutionResult:
        """Send one risk-approved order to Binance Spot Testnet."""
        if self.control.mode is not AutonomousMode.TESTNET:
            return self._rejected("Testnet mode is required")
        if not self.control.can_run():
            return self._rejected("autonomous control does not permit Testnet execution")
        if not risk_decision.approved or risk_decision.reason is not RiskReason.APPROVED:
            return self._rejected("order was not approved by the deterministic risk gateway")
        if risk_decision.order_id != order.client_order_id:
            return self._rejected("risk decision does not match the order")
        if order.symbol != candle.symbol or order.timeframe != candle.timeframe:
            return self._rejected("order symbol/timeframe must match execution candle")
        if self.policy.require_account_preflight and not self._preflight_ok:
            return self._rejected("Testnet account preflight is required before execution")

        try:
            simulated_order, fill = self.client.execute(order, candle)
        except Exception as exc:  # boundary converts exchange failures to safe rejection
            return ExecutionResult(False, f"Binance Testnet execution failed: {exc}", None, None)

        return ExecutionResult(
            accepted=simulated_order.status.value != "REJECTED",
            reason=simulated_order.reason,
            simulated_order=simulated_order,
            fill=fill,
        )

    def _require_testnet_control(self) -> None:
        if self.control.mode is not AutonomousMode.TESTNET:
            raise RuntimeError("Testnet mode is required")
        if not self.control.can_run():
            raise RuntimeError("autonomous control does not permit Testnet execution")

    @staticmethod
    def _rejected(reason: str) -> ExecutionResult:
        return ExecutionResult(False, reason, None, None)
