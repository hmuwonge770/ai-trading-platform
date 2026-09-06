from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from packages.database.models import MarketCandle


class InvalidKline(ValueError):
    """Raised when a Binance kline row is malformed."""


def _decimal(value: Any, field: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise InvalidKline(f"invalid {field}: {value!r}") from exc


def _timestamp(value: Any, field: str) -> datetime:
    try:
        milliseconds = int(value)
    except (TypeError, ValueError) as exc:
        raise InvalidKline(f"invalid {field}: {value!r}") from exc
    return datetime.fromtimestamp(milliseconds / 1000, tz=UTC)


def parse_kline(row: Any, symbol: str, timeframe: str) -> MarketCandle:
    """Convert Binance's 12-field kline tuple into our canonical candle model."""
    if not isinstance(row, (list, tuple)) or len(row) < 9:
        raise InvalidKline("kline must contain at least 9 fields")
    if not symbol or symbol != symbol.upper():
        raise InvalidKline("symbol must be uppercase")
    if not timeframe:
        raise InvalidKline("timeframe is required")

    candle = MarketCandle(
        symbol=symbol,
        timeframe=timeframe,
        open_time=_timestamp(row[0], "open_time"),
        close_time=_timestamp(row[6], "close_time"),
        open=_decimal(row[1], "open"),
        high=_decimal(row[2], "high"),
        low=_decimal(row[3], "low"),
        close=_decimal(row[4], "close"),
        volume=_decimal(row[5], "volume"),
        quote_volume=_decimal(row[7], "quote_volume"),
        trade_count=int(row[8]),
    )
    if candle.high < candle.low:
        raise InvalidKline("high cannot be lower than low")
    if candle.open_time > candle.close_time:
        raise InvalidKline("open_time cannot be after close_time")
    return candle
