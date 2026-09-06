from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
import hmac

import httpx
import pytest

from packages.execution.binance_testnet import (
    TESTNET_BASE_URL,
    BinanceSpotTestnetClient,
    BinanceTestnetConfig,
    BinanceTestnetError,
)
from packages.strategies.models import MarketBar, Signal
from packages.trading.paper import OrderIntent


SECRET = "test-secret"


def order_intent(side: Signal = Signal.BUY) -> OrderIntent:
    from uuid import uuid4

    signal_id = uuid4()
    return OrderIntent(
        intent_id=uuid4(),
        signal_id=signal_id,
        strategy_version_id="strategy-1",
        symbol="BTCUSDT",
        timeframe="1m",
        side=side,
        quantity=Decimal("0.01000000"),
        reference_price=Decimal("100000"),
        client_order_id="stage17-test-001",
        reason="test",
    )


def candle() -> MarketBar:
    return MarketBar(
        symbol="BTCUSDT",
        timeframe="1m",
        open_time=datetime(2026, 9, 6, tzinfo=UTC),
        open=Decimal("100000"),
        high=Decimal("101000"),
        low=Decimal("99000"),
        close=Decimal("100500"),
        volume=Decimal("10"),
    )


def test_config_rejects_non_testnet_endpoint() -> None:
    with pytest.raises(ValueError, match="only permits"):
        BinanceTestnetConfig("key", SECRET, base_url="https://api.binance.com")


def test_config_rejects_empty_credentials() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        BinanceTestnetConfig("", SECRET)


def test_signed_order_request_contains_api_key_and_valid_hmac() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.headers["X-MBX-APIKEY"] == "test-key"
        query = dict(request.url.params)
        supplied = query.pop("signature")
        payload = "&".join(f"{key}={value}" for key, value in query.items())
        expected = hmac.new(SECRET.encode(), payload.encode(), sha256).hexdigest()
        assert supplied == expected
        return httpx.Response(
            200,
            json={
                "symbol": "BTCUSDT",
                "orderId": 123,
                "clientOrderId": "stage17-test-001",
                "status": "FILLED",
                "executedQty": "0.01000000",
                "cummulativeQuoteQty": "1000.00",
                "fills": [],
            },
            request=request,
        )

    http = httpx.Client(
        base_url=TESTNET_BASE_URL,
        transport=httpx.MockTransport(handler),
    )
    adapter = BinanceSpotTestnetClient(
        BinanceTestnetConfig("test-key", SECRET),
        client=http,
        clock_ms=lambda: 1_757_000_000_000,
    )
    result = adapter.place_market_order(order_intent())

    assert result["status"] == "FILLED"
    assert len(requests) == 1
    assert requests[0].url.path == "/api/v3/order"


def test_execute_maps_testnet_fill_to_execution_contract() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "symbol": "BTCUSDT",
                "orderId": 123,
                "clientOrderId": "stage17-test-001",
                "status": "FILLED",
                "executedQty": "0.01000000",
                "cummulativeQuoteQty": "1000.00",
            },
            request=request,
        )

    http = httpx.Client(base_url=TESTNET_BASE_URL, transport=httpx.MockTransport(handler))
    adapter = BinanceSpotTestnetClient(BinanceTestnetConfig("key", SECRET), client=http)
    simulated_order, fill = adapter.execute(order_intent(), candle())

    assert simulated_order.status.value == "filled"
    assert simulated_order.filled_quantity == Decimal("0.01000000")
    assert fill is not None
    assert fill.price == Decimal("100000")


def test_binance_error_does_not_expose_secret() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"code": -2010, "msg": "insufficient balance"}, request=request)

    http = httpx.Client(base_url=TESTNET_BASE_URL, transport=httpx.MockTransport(handler))
    adapter = BinanceSpotTestnetClient(BinanceTestnetConfig("key", SECRET), client=http)

    with pytest.raises(BinanceTestnetError) as exc:
        adapter.place_market_order(order_intent())

    assert SECRET not in str(exc.value)
    assert "insufficient balance" in str(exc.value)


def test_market_order_validates_symbol() -> None:
    order = order_intent()
    bad_order = OrderIntent(
        intent_id=order.intent_id,
        signal_id=order.signal_id,
        strategy_version_id=order.strategy_version_id,
        symbol="btcusdt",
        timeframe=order.timeframe,
        side=order.side,
        quantity=order.quantity,
        reference_price=order.reference_price,
        client_order_id=order.client_order_id,
        reason=order.reason,
    )
    adapter = BinanceSpotTestnetClient(BinanceTestnetConfig("key", SECRET))
    try:
        with pytest.raises(ValueError, match="uppercase"):
            adapter.place_market_order(bad_order)
    finally:
        adapter.close()
