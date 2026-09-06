from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import httpx

from packages.execution import (
    BinanceSpotTestnetClient,
    BinanceTestnetConfig,
    ExecutionService,
    TestnetE2EHarness,
)
from packages.risk import RiskDecision, RiskReason
from packages.strategies.models import MarketBar, Signal
from packages.trading.paper import OrderIntent


def make_order() -> OrderIntent:
    signal_id = uuid4()
    return OrderIntent(
        intent_id=uuid4(),
        signal_id=signal_id,
        strategy_version_id=str(uuid4()),
        symbol="BTCUSDT",
        timeframe="1m",
        side=Signal.BUY,
        quantity=Decimal("0.001"),
        reference_price=Decimal("100"),
        client_order_id="testnet-e2e-1",
        reason="stage 26 testnet e2e",
    )


def make_candle() -> MarketBar:
    return MarketBar(
        symbol="BTCUSDT",
        timeframe="1m",
        open_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
        open=Decimal("100"),
        high=Decimal("101"),
        low=Decimal("99"),
        close=Decimal("100.5"),
        volume=Decimal("10"),
    )


def approved(order: OrderIntent) -> RiskDecision:
    return RiskDecision(
        approved=True,
        reason=RiskReason.APPROVED,
        message="approved for testnet e2e",
        order_id=order.client_order_id,
        order_notional=Decimal("0.1"),
        projected_position_notional=Decimal("0.1"),
        projected_total_exposure=Decimal("0.1"),
    )


def test_full_testnet_e2e_uses_ping_account_and_order_boundary() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/api/v3/ping":
            return httpx.Response(200, json={})
        if request.url.path == "/api/v3/account":
            assert request.headers["X-MBX-APIKEY"] == "test-key"
            assert request.url.params.get("signature")
            assert request.url.params.get("timestamp")
            return httpx.Response(200, json={"balances": []})
        if request.url.path == "/api/v3/order":
            assert request.method == "POST"
            assert request.headers["X-MBX-APIKEY"] == "test-key"
            assert request.url.params.get("signature")
            assert request.url.params.get("newClientOrderId") == "testnet-e2e-1"
            return httpx.Response(
                200,
                json={
                    "status": "FILLED",
                    "executedQty": "0.001",
                    "cummulativeQuoteQty": "0.1",
                },
            )
        return httpx.Response(404)

    client = httpx.Client(
        base_url="https://testnet.binance.vision",
        transport=httpx.MockTransport(handler),
    )
    adapter = BinanceSpotTestnetClient(
        BinanceTestnetConfig(api_key="test-key", api_secret="test-secret"),
        client=client,
        clock_ms=lambda: 1_700_000_000_000,
    )
    order = make_order()
    result = TestnetE2EHarness(adapter, ExecutionService(adapter)).run(
        order,
        approved(order),
        make_candle(),
    )

    assert result.ping_ok is True
    assert result.account_ok is True
    assert result.execution.accepted is True
    assert result.execution.fill is not None
    assert result.execution.fill.quantity == Decimal("0.001")
    assert [request.url.path for request in requests] == [
        "/api/v3/ping",
        "/api/v3/account",
        "/api/v3/order",
    ]
    client.close()


def test_testnet_e2e_requires_independent_risk_approval() -> None:
    client = httpx.Client(
        base_url="https://testnet.binance.vision",
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={})),
    )
    adapter = BinanceSpotTestnetClient(
        BinanceTestnetConfig(api_key="test-key", api_secret="test-secret"),
        client=client,
    )
    order = make_order()
    rejected = RiskDecision(
        approved=False,
        reason=RiskReason.ORDER_NOTIONAL_LIMIT,
        message="rejected",
        order_id=order.client_order_id,
        order_notional=Decimal("1000"),
        projected_position_notional=Decimal("1000"),
        projected_total_exposure=Decimal("1000"),
    )

    try:
        TestnetE2EHarness(adapter, ExecutionService(adapter)).run(order, rejected, make_candle())
    except PermissionError as exc:
        assert "independently approved" in str(exc)
    else:
        raise AssertionError("unapproved risk decision must block Testnet E2E")
    finally:
        client.close()


def test_testnet_e2e_rejects_non_testnet_endpoint() -> None:
    client = httpx.Client(
        base_url="https://api.binance.com",
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={})),
    )
    try:
        adapter = BinanceSpotTestnetClient(
            BinanceTestnetConfig(
                api_key="test-key",
                api_secret="test-secret",
                base_url="https://api.binance.com",
            ),
            client=client,
        )
    except ValueError as exc:
        assert "Spot Testnet endpoint" in str(exc)
    else:
        raise AssertionError("production Binance endpoint must be rejected")
    finally:
        client.close()
