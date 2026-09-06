from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


class Signal(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(frozen=True, slots=True)
class MarketBar:
    symbol: str
    timeframe: str
    open_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


@dataclass(frozen=True, slots=True)
class StrategySignal:
    symbol: str
    timeframe: str
    open_time: datetime
    signal: Signal
    price: Decimal
    reason: str
    indicators: dict[str, str] = field(default_factory=dict)
