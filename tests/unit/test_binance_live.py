from decimal import Decimal
from uuid import uuid4

import httpx
import pytest

from packages.execution.binance_live import (
    BINANCE_LIVE_BASE_URL,
    BinanceLiveConfig,
    BinanceSpotLiveClient,
)
from packages.strategies.models import Signal
from packages.trading.paper import OrderIntent


def test_live_config_requires_production_endpoint():
    with pytest.raises(ValueError, match="production endpoint"):
        BinanceLiveConfig("key", "secret", "https://testnet.binance.vision")


def test_live_config_rejects_empty_credentials():
    with pytest.raises(ValueError, match="credentials"):
        BinanceLiveConfig("", "secret")


def test_healthcheck_uses_injected_transport():
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json={}))
    client = httpx.Client(base_url=BINANCE_LIVE_BASE_URL, transport=transport)
    adapter = BinanceSpotLiveClient(BinanceLiveConfig("key", "secret"), client=client)
    assert adapter.healthcheck() is True
    client.close()


def test_healthcheck_fails_closed_on_transport_error():
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(503, json={"msg": "unavailable"})
    )
    client = httpx.Client(base_url=BINANCE_LIVE_BASE_URL, transport=transport)
    adapter = BinanceSpotLiveClient(BinanceLiveConfig("key", "secret"), client=client)
    assert adapter.healthcheck() is False
    client.close()


def test_submit_order_rejects_invalid_quantity():
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json={}))
    client = httpx.Client(base_url=BINANCE_LIVE_BASE_URL, transport=transport)
    adapter = BinanceSpotLiveClient(BinanceLiveConfig("key", "secret"), client=client)
    order = OrderIntent(
        intent_id=uuid4(),
        signal_id=uuid4(),
        strategy_version_id="strategy-v1",
        symbol="BTCUSDT",
        timeframe="1m",
        side=Signal.BUY,
        quantity=Decimal("0"),
        reference_price=Decimal("100"),
        client_order_id="test-order",
        reason="unit-test",
    )
    with pytest.raises(ValueError, match="quantity"):
        adapter.submit_order(order)
    client.close()
