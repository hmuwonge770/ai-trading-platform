from decimal import Decimal

import httpx
import pytest

from packages.execution.binance_live import (
    BINANCE_LIVE_BASE_URL,
    BinanceLiveConfig,
    BinanceSpotLiveClient,
)


def test_live_config_requires_production_endpoint():
    with pytest.raises(ValueError, match="production endpoint"):
        BinanceLiveConfig("key", "secret", "https://testnet.binance.vision")


def test_live_config_rejects_empty_credentials():
    with pytest.raises(ValueError, match="credentials"):
        BinanceLiveConfig("", "secret")


def test_healthcheck_uses_injected_transport():
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={}))
    client = httpx.Client(base_url=BINANCE_LIVE_BASE_URL, transport=transport)
    adapter = BinanceSpotLiveClient(
        BinanceLiveConfig("key", "secret"), client=client
    )
    assert adapter.healthcheck() is True
    client.close()


def test_healthcheck_fails_closed_on_transport_error():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(503, json={"msg": "unavailable"})
    )
    client = httpx.Client(base_url=BINANCE_LIVE_BASE_URL, transport=transport)
    adapter = BinanceSpotLiveClient(
        BinanceLiveConfig("key", "secret"), client=client
    )
    assert adapter.healthcheck() is False
    client.close()


def test_submit_order_rejects_invalid_quantity():
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={}))
    client = httpx.Client(base_url=BINANCE_LIVE_BASE_URL, transport=transport)
    adapter = BinanceSpotLiveClient(
        BinanceLiveConfig("key", "secret"), client=client
    )
    order = type("Order", (), {
        "side": type("Side", (), {"value": "BUY"})(),
        "quantity": Decimal("0"),
        "symbol": "BTCUSDT",
        "client_order_id": "test-order",
    })()
    with pytest.raises(ValueError, match="quantity"):
        adapter.submit_order(order)
    client.close()
