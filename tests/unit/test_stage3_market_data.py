from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest

from packages.market_data.binance import BinanceKlineClient
from packages.market_data.parser import InvalidKline, parse_kline


def kline(open_time: int, close_time: int, close: str = "101.5") -> list[object]:
    return [
        open_time,
        "100.0",
        "103.0",
        "99.0",
        close,
        "12.345",
        close_time,
        "1234.500",
        42,
        "6.000",
        "600.000",
        "0",
    ]


def test_parse_kline_normalizes_binance_row():
    candle = parse_kline(kline(1_700_000_000_000, 1_700_000_059_999), "BTCUSDT", "1m")

    assert candle.symbol == "BTCUSDT"
    assert candle.timeframe == "1m"
    assert candle.open_time == datetime.fromtimestamp(1_700_000_000, tz=UTC)
    assert candle.close == Decimal("101.5")
    assert candle.volume == Decimal("12.345")
    assert candle.quote_volume == Decimal("1234.500")
    assert candle.trade_count == 42


def test_parse_kline_rejects_malformed_rows():
    with pytest.raises(InvalidKline):
        parse_kline([1, "100"], "BTCUSDT", "1m")

    invalid = kline(1_700_000_060_000, 1_700_000_059_999)
    with pytest.raises(InvalidKline):
        parse_kline(invalid, "BTCUSDT", "1m")


@pytest.mark.asyncio
async def test_binance_client_paginates_without_overlap():
    pages = [
        [kline(1000, 1999), kline(2000, 2999)],
        [kline(3000, 3999)],
    ]
    requests: list[dict[str, str]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(dict(request.url.params))
        return httpx.Response(200, json=pages.pop(0))

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://api.binance.com"
    ) as http_client:
        client = BinanceKlineClient(client=http_client)
        received = []
        async for page in client.iter_klines(
            "BTCUSDT",
            "1m",
            datetime.fromtimestamp(1, tz=UTC),
            datetime.fromtimestamp(4, tz=UTC),
            limit=2,
        ):
            received.append(page)

    assert len(received) == 2
    assert len(requests) == 2
    assert requests[0]["startTime"] == "1000"
    assert requests[1]["startTime"] == "2001"
    assert requests[0]["limit"] == "2"


@pytest.mark.asyncio
async def test_binance_client_retries_rate_limit():
    attempts = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(200, json=[kline(1000, 1999)])

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://api.binance.com"
    ) as http_client:
        client = BinanceKlineClient(client=http_client, max_retries=1, backoff_seconds=0)
        rows = await client.get_klines("BTCUSDT", "1m", limit=1)

    assert attempts == 2
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_binance_client_validates_request():
    client = BinanceKlineClient(max_retries=0)
    with pytest.raises(ValueError):
        await client.get_klines("btcusdt", "1m")
    with pytest.raises(ValueError):
        await client.get_klines("BTCUSDT", "1m", limit=1001)
