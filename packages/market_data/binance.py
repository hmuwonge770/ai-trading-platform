from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

import httpx


class BinanceMarketDataError(RuntimeError):
    """Raised when Binance market data cannot be retrieved."""


class BinanceKlineClient:
    """Small async client for Binance Spot public kline data."""

    path = "/api/v3/klines"
    max_limit = 1000

    def __init__(
        self,
        base_url: str = "https://api.binance.com",
        timeout: float = 20.0,
        max_retries: int = 4,
        backoff_seconds: float = 1.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> "BinanceKlineClient":
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def get_klines(
        self,
        symbol: str,
        interval: str,
        *,
        start_time_ms: int | None = None,
        end_time_ms: int | None = None,
        limit: int = max_limit,
    ) -> list[list[Any]]:
        if not symbol or symbol != symbol.upper():
            raise ValueError("symbol must be a non-empty uppercase Binance symbol")
        if not interval:
            raise ValueError("interval is required")
        if not 1 <= limit <= self.max_limit:
            raise ValueError(f"limit must be between 1 and {self.max_limit}")
        if start_time_ms is not None and end_time_ms is not None and start_time_ms > end_time_ms:
            raise ValueError("start_time_ms cannot be after end_time_ms")

        params: dict[str, Any] = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
        }
        if start_time_ms is not None:
            params["startTime"] = start_time_ms
        if end_time_ms is not None:
            params["endTime"] = end_time_ms

        client = self._client or httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)
        temporary = self._client is None
        try:
            for attempt in range(self.max_retries + 1):
                try:
                    response = await client.get(self.path, params=params)
                    if response.status_code == 429 or response.status_code >= 500:
                        if attempt >= self.max_retries:
                            response.raise_for_status()
                        retry_after = response.headers.get("Retry-After")
                        delay = (
                            float(retry_after)
                            if retry_after is not None
                            else self.backoff_seconds * (2**attempt)
                        )
                        await asyncio.sleep(delay)
                        continue
                    response.raise_for_status()
                    data = response.json()
                    if not isinstance(data, list):
                        raise BinanceMarketDataError("Binance returned a non-list kline payload")
                    return data
                except (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError):
                    if attempt >= self.max_retries:
                        raise BinanceMarketDataError("Binance request failed after retries") from None
                    await asyncio.sleep(self.backoff_seconds * (2**attempt))
        finally:
            if temporary:
                await client.aclose()

        raise BinanceMarketDataError("Binance request failed")

    async def iter_klines(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime,
        *,
        limit: int = max_limit,
    ) -> AsyncIterator[list[list[Any]]]:
        """Yield pages in chronological order without overlapping requests."""
        if start.tzinfo is None or end.tzinfo is None:
            raise ValueError("start and end must be timezone-aware")
        if start > end:
            raise ValueError("start cannot be after end")

        cursor = int(start.timestamp() * 1000)
        end_ms = int(end.timestamp() * 1000)
        while cursor <= end_ms:
            page = await self.get_klines(
                symbol,
                interval,
                start_time_ms=cursor,
                end_time_ms=end_ms,
                limit=limit,
            )
            if not page:
                return
            yield page
            last_open = int(page[-1][0])
            next_cursor = last_open + 1
            if next_cursor <= cursor:
                raise BinanceMarketDataError("Binance returned non-advancing kline pages")
            cursor = next_cursor
            if len(page) < limit:
                return
