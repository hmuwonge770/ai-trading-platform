"""Controlled Binance Spot Testnet execution boundary for autonomous trading."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from packages.autonomy.control import AutonomousControl, AutonomousMode
from packages.execution.service import ExecutionResult
from packages.risk import RiskDecision, RiskReason
from packages.strategies.models import MarketBar
from packages.trading.paper import OrderIntent


class TestnetExecutionTransport(Protocol):
    def ping(self) -> None: ...
    def get_account(self) -> dict[str, Any]: ...
    def execute(self, order: OrderIntent, candle: MarketBar): ...


@dataclass(frozen=True, slots=True)
class TestnetExecutionPolicy:
    """Explicit gates required before an autonomous Testnet order is sent."""

    require_account_preflight: bool = True


class BinanceTestnetExecutionSubmitter:
    """Adapt a Binance Spot Testnet client to autonomous execution.

    The underlying exchange adapter is hard-wired to Spot Testnet. This boundary
    adds the independent autonomous TESTNET control and account preflight gates.
    """

    def __init__(
        self,
        control: AutonomousControl,
        client: TestnetExecutionTransport,
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
            account = self.client.get_account()
            if not isinstance(account, dict):
                raise RuntimeError("Binance Testnet account preflight returned an invalid payload")
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
        except Exception as exc:  # exchange failures must not become false success
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
