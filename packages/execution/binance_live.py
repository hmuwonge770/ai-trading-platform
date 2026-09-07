"""Explicit production Binance adapter kept outside the autonomy package.

Credentials are injected at construction time and are never exposed to the
AI/autonomy layer. The adapter only exposes healthcheck and market-order
submission; upstream authorization and risk gates remain mandatory.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from urllib.parse import urlencode

import httpx

from packages.trading.paper import OrderIntent


BINANCE_LIVE_BASE_URL = "https://api.binance.com"


class BinanceLiveError(RuntimeError):
    """Raised when the production Binance adapter cannot process a request."""


@dataclass(frozen=True, slots=True)
class BinanceLiveConfig:
    api_key: str
    api_secret: str
    base_url: str = BINANCE_LIVE_BASE_URL
    recv_window_ms: int = 5_000
    timeout_seconds: float = 20.0

    def __post_init__(self) -> None:
        if not self.api_key.strip() or not self.api_secret.strip():
            raise ValueError("Binance live credentials must not be empty")
        if self.base_url.rstrip("/") != BINANCE_LIVE_BASE_URL:
            raise ValueError("live adapter only permits the Binance production endpoint")
        if not 1 <= self.recv_window_ms <= 60_000:
            raise ValueError("recv_window_ms must be between 1 and 60000")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")


class BinanceSpotLiveClient:
    """Minimal production Spot adapter with injected credentials."""

    order_path = "/api/v3/order"
    ping_path = "/api/v3/ping"

    def __init__(
        self,
        config: BinanceLiveConfig,
        *,
        client: httpx.Client | None = None,
        clock_ms: Callable[[], int] | None = None,
    ) -> None:
        self.config = config
        self._client = client or httpx.Client(
            base_url=BINANCE_LIVE_BASE_URL,
            timeout=config.timeout_seconds,
            headers={"X-MBX-APIKEY": config.api_key},
        )
        self._owns_client = client is None
        self._clock_ms = clock_ms or (lambda: int(time.time() * 1000))

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "BinanceSpotLiveClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def healthcheck(self) -> bool:
        try:
            response = self._client.get(self.ping_path)
            self._raise_for_binance(response)
            return True
        except (BinanceLiveError, httpx.HTTPError):
            return False

    def submit_order(self, order: OrderIntent) -> dict[str, Any]:
        if order.side.value not in {"BUY", "SELL"}:
            raise ValueError("Binance Spot accepts only BUY or SELL orders")
        if order.quantity <= 0:
            raise ValueError("order quantity must be greater than zero")
        if not order.symbol.strip() or order.symbol != order.symbol.upper():
            raise ValueError("order symbol must be a non-empty uppercase Binance symbol")
        if not order.client_order_id.strip():
            raise ValueError("client_order_id must not be empty")

        payload = self._signed_request(
            "POST",
            self.order_path,
            {
                "symbol": order.symbol,
                "side": order.side.value,
                "type": "MARKET",
                "quantity": format(order.quantity, "f"),
                "newClientOrderId": order.client_order_id,
                "newOrderRespType": "FULL",
            },
        )
        if not isinstance(payload, dict):
            raise BinanceLiveError("Binance returned an invalid order payload")
        return payload

    def _signed_request(self, method: str, path: str, params: dict[str, Any]) -> Any:
        signed = dict(params)
        signed["timestamp"] = self._clock_ms()
        signed["recvWindow"] = self.config.recv_window_ms
        query = urlencode(signed, doseq=True)
        signed["signature"] = hmac.new(
            self.config.api_secret.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
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
                raise BinanceLiveError(
                    f"Binance error {payload.get('code', 'unknown')}: "
                    f"{payload.get('msg', 'Binance request failed')}"
                )
            raise BinanceLiveError(f"Binance HTTP error {response.status_code}")
        return payload
