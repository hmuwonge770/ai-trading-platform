from __future__ import annotations

import hashlib
import hmac
import time
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from urllib.parse import urlencode
from uuid import uuid4

import httpx

from packages.execution.simulator import ExecutionStatus, SimulatedFill, SimulatedOrder
from packages.strategies.models import MarketBar, Signal
from packages.trading.paper import OrderIntent


TESTNET_BASE_URL = "https://testnet.binance.vision"


class BinanceTestnetError(RuntimeError):
    """Raised when the Binance Spot Testnet rejects or cannot process a request."""


@dataclass(frozen=True, slots=True)
class BinanceTestnetConfig:
    api_key: str
    api_secret: str
    base_url: str = TESTNET_BASE_URL
    recv_window_ms: int = 5_000
    timeout_seconds: float = 20.0

    def __post_init__(self) -> None:
        if not self.api_key.strip() or not self.api_secret.strip():
            raise ValueError("Binance Testnet API credentials must not be empty")
        if self.base_url.rstrip("/") != TESTNET_BASE_URL:
            raise ValueError("Stage 17 only permits the Binance Spot Testnet endpoint")
        if not 1 <= self.recv_window_ms <= 60_000:
            raise ValueError("recv_window_ms must be between 1 and 60000")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")


class BinanceSpotTestnetClient:
    """Minimal signed Spot Testnet client for market-order execution.

    This adapter is deliberately hard-wired to the Spot Testnet URL. It cannot
    be configured to target Binance production, which keeps the live boundary
    outside Stage 17.
    """

    order_path = "/api/v3/order"
    account_path = "/api/v3/account"
    ping_path = "/api/v3/ping"

    def __init__(
        self,
        config: BinanceTestnetConfig,
        *,
        client: httpx.Client | None = None,
        clock_ms: Callable[[], int] | None = None,
    ) -> None:
        self.config = config
        self._client = client or httpx.Client(
            base_url=TESTNET_BASE_URL,
            timeout=config.timeout_seconds,
            headers={"X-MBX-APIKEY": config.api_key},
        )
        self._client.headers["X-MBX-APIKEY"] = config.api_key
        self._owns_client = client is None
        self._clock_ms = clock_ms or (lambda: int(time.time() * 1000))

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "BinanceSpotTestnetClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def ping(self) -> None:
        response = self._client.get(self.ping_path)
        self._raise_for_binance(response)

    def get_account(self) -> dict[str, Any]:
        payload = self._signed_request("GET", self.account_path, {})
        if not isinstance(payload, dict):
            raise BinanceTestnetError("Binance returned an invalid account payload")
        return payload

    def place_market_order(self, order: OrderIntent) -> dict[str, Any]:
        if order.side not in {Signal.BUY, Signal.SELL}:
            raise ValueError("Binance Spot Testnet accepts only BUY or SELL orders")
        if order.quantity <= 0:
            raise ValueError("order quantity must be greater than zero")
        if not order.symbol.strip() or order.symbol != order.symbol.upper():
            raise ValueError("order symbol must be a non-empty uppercase Binance symbol")
        if not order.client_order_id.strip():
            raise ValueError("client_order_id must not be empty")

        params = {
            "symbol": order.symbol,
            "side": order.side.value,
            "type": "MARKET",
            "quantity": self._decimal(order.quantity),
            "newClientOrderId": order.client_order_id,
            "newOrderRespType": "FULL",
        }
        payload = self._signed_request("POST", self.order_path, params)
        if not isinstance(payload, dict):
            raise BinanceTestnetError("Binance returned an invalid order payload")
        return payload

    def execute(self, order: OrderIntent, candle: MarketBar) -> tuple[SimulatedOrder, SimulatedFill | None]:
        """Adapt a Testnet market-order response to the Stage 16 backend contract."""
        if order.symbol != candle.symbol or order.timeframe != candle.timeframe:
            raise ValueError("order symbol/timeframe must match execution candle")
        response = self.place_market_order(order)
        status = str(response.get("status", "UNKNOWN"))
        simulation_id = uuid4()
        executed_qty = Decimal(str(response.get("executedQty", "0")))
        quote_qty = Decimal(str(response.get("cummulativeQuoteQty", "0")))
        average_price = quote_qty / executed_qty if executed_qty else None

        mapped_status = {
            "NEW": ExecutionStatus.ACCEPTED,
            "PARTIALLY_FILLED": ExecutionStatus.PARTIALLY_FILLED,
            "FILLED": ExecutionStatus.FILLED,
            "CANCELED": ExecutionStatus.CANCELED,
            "EXPIRED": ExecutionStatus.CANCELED,
            "REJECTED": ExecutionStatus.REJECTED,
        }.get(status, ExecutionStatus.REJECTED)
        reason = "Binance Spot Testnet order accepted"
        if mapped_status == ExecutionStatus.REJECTED:
            reason = "Binance Spot Testnet returned an unsupported or rejected order status"

        simulated_order = SimulatedOrder(
            simulation_id=simulation_id,
            order_id=order.client_order_id,
            status=mapped_status,
            requested_quantity=order.quantity,
            filled_quantity=executed_qty,
            remaining_quantity=max(Decimal("0"), order.quantity - executed_qty),
            average_fill_price=average_price,
            reason=reason,
        )
        if executed_qty <= 0 or average_price is None:
            return simulated_order, None

        fill = SimulatedFill(
            fill_id=uuid4(),
            simulation_id=simulation_id,
            order_id=order.client_order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=executed_qty,
            price=average_price,
            executed_at=candle.open_time,
        )
        return simulated_order, fill

    def _signed_request(self, method: str, path: str, params: dict[str, Any]) -> Any:
        signed = dict(params)
        signed["timestamp"] = self._clock_ms()
        signed["recvWindow"] = self.config.recv_window_ms
        query = urlencode(signed, doseq=True)
        signature = hmac.new(
            self.config.api_secret.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        signed["signature"] = signature
        response = self._client.request(method, path, params=signed)
        return self._raise_for_binance(response)

    @staticmethod
    def _raise_for_binance(response: httpx.Response) -> Any:
        try:
            payload = response.json()
        except ValueError:
            payload = None
        if response.is_error:
            if isinstance(payload, dict):
                code = payload.get("code", "unknown")
                message = payload.get("msg", "Binance request failed")
                raise BinanceTestnetError(f"Binance error {code}: {message}")
            raise BinanceTestnetError(f"Binance HTTP error {response.status_code}")
        return payload

    @staticmethod
    def _decimal(value: Decimal) -> str:
        return format(value, "f")
