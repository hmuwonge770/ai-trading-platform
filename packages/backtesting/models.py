from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from packages.strategies.models import Signal


@dataclass(frozen=True, slots=True)
class BacktestTrade:
    symbol: str
    entry_time: datetime
    exit_time: datetime
    entry_price: Decimal
    exit_price: Decimal
    quantity: Decimal
    gross_pnl: Decimal
    entry_fee: Decimal
    exit_fee: Decimal
    net_pnl: Decimal


@dataclass(frozen=True, slots=True)
class EquityPoint:
    time: datetime
    equity: Decimal
    cash: Decimal
    position_value: Decimal


@dataclass(frozen=True, slots=True)
class BacktestResult:
    initial_capital: Decimal
    final_equity: Decimal
    total_return: Decimal
    total_fees: Decimal
    max_drawdown: Decimal
    trades: tuple[BacktestTrade, ...]
    equity_curve: tuple[EquityPoint, ...]

    @property
    def winning_trades(self) -> int:
        return sum(1 for trade in self.trades if trade.net_pnl > 0)

    @property
    def losing_trades(self) -> int:
        return sum(1 for trade in self.trades if trade.net_pnl < 0)

    @property
    def win_rate(self) -> Decimal:
        if not self.trades:
            return Decimal("0")
        return Decimal(self.winning_trades) / Decimal(len(self.trades))


@dataclass(frozen=True, slots=True)
class BacktestSignal:
    time: datetime
    signal: Signal
