from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from packages.backtesting.models import BacktestResult, BacktestTrade, EquityPoint
from packages.strategies.base import Strategy
from packages.strategies.models import MarketBar, Signal


class BacktestEngine:
    """Simple long-only, all-in strategy simulator for historical research.

    Signals are generated from a candle close and executed at the following
    candle open. This prevents same-candle look-ahead bias.
    """

    def run(
        self,
        candles: Sequence[MarketBar],
        strategy: Strategy,
        initial_capital: Decimal,
        fee_rate: Decimal = Decimal("0"),
        slippage_rate: Decimal = Decimal("0"),
    ) -> BacktestResult:
        self._validate_inputs(candles, initial_capital, fee_rate, slippage_rate)
        if not candles:
            return BacktestResult(
                initial_capital=initial_capital,
                final_equity=initial_capital,
                total_return=Decimal("0"),
                total_fees=Decimal("0"),
                max_drawdown=Decimal("0"),
                trades=(),
                equity_curve=(),
            )

        signals = strategy.generate_signals(candles)
        if len(signals) != len(candles):
            raise ValueError("strategy must return exactly one signal per candle")

        cash = initial_capital
        quantity = Decimal("0")
        entry_price = Decimal("0")
        entry_fee = Decimal("0")
        entry_time = candles[0].open_time
        trades: list[BacktestTrade] = []
        equity_curve: list[EquityPoint] = []
        peak_equity = initial_capital
        max_drawdown = Decimal("0")
        total_fees = Decimal("0")

        for index, candle in enumerate(candles):
            # A signal generated on the previous candle executes at this candle's open.
            if index > 0:
                signal = signals[index - 1].signal
                execution_price = candle.open

                if signal == Signal.BUY and quantity == 0:
                    execution_price *= Decimal("1") + slippage_rate
                    quantity = cash / (execution_price * (Decimal("1") + fee_rate))
                    entry_fee = quantity * execution_price * fee_rate
                    cash -= quantity * execution_price + entry_fee
                    entry_price = execution_price
                    entry_time = candle.open_time
                    total_fees += entry_fee

                elif signal == Signal.SELL and quantity > 0:
                    execution_price *= Decimal("1") - slippage_rate
                    gross_proceeds = quantity * execution_price
                    exit_fee = gross_proceeds * fee_rate
                    cash += gross_proceeds - exit_fee
                    gross_pnl = quantity * (execution_price - entry_price)
                    net_pnl = gross_pnl - entry_fee - exit_fee
                    trades.append(
                        BacktestTrade(
                            symbol=candle.symbol,
                            entry_time=entry_time,
                            exit_time=candle.open_time,
                            entry_price=entry_price,
                            exit_price=execution_price,
                            quantity=quantity,
                            gross_pnl=gross_pnl,
                            entry_fee=entry_fee,
                            exit_fee=exit_fee,
                            net_pnl=net_pnl,
                        )
                    )
                    total_fees += exit_fee
                    quantity = Decimal("0")
                    entry_price = Decimal("0")
                    entry_fee = Decimal("0")

            position_value = quantity * candle.close
            equity = cash + position_value
            peak_equity = max(peak_equity, equity)
            drawdown = Decimal("0") if peak_equity == 0 else (peak_equity - equity) / peak_equity
            max_drawdown = max(max_drawdown, drawdown)
            equity_curve.append(
                EquityPoint(
                    time=candle.open_time,
                    equity=equity,
                    cash=cash,
                    position_value=position_value,
                )
            )

        final_equity = equity_curve[-1].equity
        return BacktestResult(
            initial_capital=initial_capital,
            final_equity=final_equity,
            total_return=(final_equity - initial_capital) / initial_capital,
            total_fees=total_fees,
            max_drawdown=max_drawdown,
            trades=tuple(trades),
            equity_curve=tuple(equity_curve),
        )

    @staticmethod
    def _validate_inputs(
        candles: Sequence[MarketBar],
        initial_capital: Decimal,
        fee_rate: Decimal,
        slippage_rate: Decimal,
    ) -> None:
        if initial_capital <= 0:
            raise ValueError("initial_capital must be greater than zero")
        if fee_rate < 0 or fee_rate >= 1:
            raise ValueError("fee_rate must be between zero and one")
        if slippage_rate < 0 or slippage_rate >= 1:
            raise ValueError("slippage_rate must be between zero and one")
        for index in range(1, len(candles)):
            if candles[index].open_time <= candles[index - 1].open_time:
                raise ValueError("candles must be strictly ordered by open_time")
