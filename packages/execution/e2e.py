from __future__ import annotations

from dataclasses import dataclass

from packages.execution.binance_testnet import BinanceSpotTestnetClient
from packages.execution.service import ExecutionResult, ExecutionService
from packages.risk import RiskDecision, RiskReason
from packages.strategies.models import MarketBar
from packages.trading.environment import EnvironmentGuard, TradingEnvironment
from packages.trading.paper import OrderIntent


@dataclass(frozen=True, slots=True)
class TestnetE2EResult:
    """Evidence returned by a complete Testnet execution smoke flow."""

    ping_ok: bool
    account_ok: bool
    execution: ExecutionResult


class TestnetE2EHarness:
    """Exercise the real execution boundary against Binance Spot Testnet.

    The harness never permits a production endpoint. CI injects an HTTP-mocked
    Binance client, while an operator can inject the real Stage 17 client for
    a credentialed Spot Testnet smoke run. No live credentials are accepted by
    this class and no promotion/live authorization is bypassed.
    """

    def __init__(
        self,
        client: BinanceSpotTestnetClient,
        execution: ExecutionService,
    ) -> None:
        self.client = client
        self.execution = execution
        EnvironmentGuard.validate(TradingEnvironment.TESTNET, client.config.base_url)

    def run(
        self,
        order: OrderIntent,
        risk_decision: RiskDecision,
        candle: MarketBar,
    ) -> TestnetE2EResult:
        """Ping, authenticate account access, then execute one risk-approved order."""
        if not risk_decision.approved or risk_decision.reason != RiskReason.APPROVED:
            raise PermissionError("Testnet E2E requires an independently approved risk decision")
        if risk_decision.order_id != order.client_order_id:
            raise PermissionError("risk decision does not match the Testnet E2E order")

        self.client.ping()
        account = self.client.get_account()
        if not isinstance(account, dict):
            raise RuntimeError("Binance Testnet account response was invalid")

        result = self.execution.submit(order, risk_decision, candle)
        return TestnetE2EResult(ping_ok=True, account_ok=True, execution=result)
