from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from packages.database.models import MarketCandle
from packages.market_data.binance import BinanceKlineClient
from packages.market_data.parser import parse_kline


class HistoricalKlineIngestor:
    """Fetch historical klines and persist them idempotently."""

    def __init__(self, client: BinanceKlineClient, db: Session) -> None:
        self.client = client
        self.db = db

    async def ingest(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
        *,
        limit: int = BinanceKlineClient.max_limit,
    ) -> int:
        """Ingest a closed date range and return the number of rows processed."""
        processed = 0
        async for page in self._pages(symbol, timeframe, start, end, limit):
            candles = [parse_kline(row, symbol, timeframe) for row in page]
            if candles:
                self._upsert(candles)
                processed += len(candles)
        return processed

    async def _pages(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
        limit: int,
    ) -> AsyncIterator[list[list[object]]]:
        async for page in self.client.iter_klines(
            symbol, timeframe, start, end, limit=limit
        ):
            yield page

    def _upsert(self, candles: list[MarketCandle]) -> None:
        rows = [
            {
                "symbol": candle.symbol,
                "timeframe": candle.timeframe,
                "open_time": candle.open_time,
                "close_time": candle.close_time,
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
                "volume": candle.volume,
                "quote_volume": candle.quote_volume,
                "trade_count": candle.trade_count,
            }
            for candle in candles
        ]
        statement = insert(MarketCandle).values(rows)
        statement = statement.on_conflict_do_update(
            constraint="uq_market_candles_symbol_timeframe_open",
            set_={
                "close_time": statement.excluded.close_time,
                "open": statement.excluded.open,
                "high": statement.excluded.high,
                "low": statement.excluded.low,
                "close": statement.excluded.close,
                "volume": statement.excluded.volume,
                "quote_volume": statement.excluded.quote_volume,
                "trade_count": statement.excluded.trade_count,
            },
        )
        self.db.execute(statement)
        self.db.commit()
