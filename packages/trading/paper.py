from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from packages.strategies.base import Strategy
from packages.strategies.models import MarketBar, Signal


@dataclass(frozen=True, slots=True)
class PaperTradingConfig:
    """Deterministic paper-execution settings.

    Paper trading has no exchange client and therefore cannot submit a real
    order. Quantity is supplied by the paper configuration until the Risk and
    Portfolio stages provide those decisions as first-class services.
    """

    initial_cash: Decimal
    order_quantity: Decimal
    fee_rate: Decimal = Decimal("0")
    slippage_rate: Decimal = Decimal("0")
    warmup_candles: int = 50

    def __post_init__(self) -> None:
        if self.initial_cash <= 0:
            raise ValueError("initial_cash must be greater than zero")
        if self.order_quantity <= 0:
            raise ValueError("order_quantity must be greater than zero")
        if self.fee_rate < 0 or self.fee_rate >= 1:
            raise ValueError("fee_rate must be between zero and one")
        if self.slippage_rate < 0 or self.slippage_rate >= 1:
            raise ValueError("slippage_rate must be between zero and one")
        if self.warmup_candles < 1:
            raise ValueError("warmup_candles must be at least one")


@dataclass(frozen=True, slots=True)
class TradingSignal:
    signal_id: UUID
    strategy_version_id: str
    symbol: str
    timeframe: str
    side: Signal
    reference_price: Decimal
    generated_at: datetime
    candle_time: datetime
    reason: str


@dataclass(frozen=True, slots=True)
class OrderIntent:
    intent_id: UUID
    signal_id: UUID
    strategy_version_id: str
    symbol: str
    timeframe: str
    side: Signal
    quantity: Decimal
    reference_price: Decimal
    client_order_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class PaperFill:
    fill_id: UUID
    intent_id: UUID
    symbol: str
    side: Signal
    quantity: Decimal
    price: Decimal
    fee: Decimal
    executed_at: datetime


@dataclass(frozen=True, slots=True)
class PaperCandleResult:
    """Result of processing one completed market candle."""

    signal: TradingSignal
    order: OrderIntent | None
    fill: PaperFill | None


class PaperTradingEngine:
    """Run a strategy against live-like candles without exchange access.

    Historical candles are used only for strategy warm-up. A signal is created
    after a candle is completed and, when actionable, becomes an order intent
    on the next candle. The next candle's open is the simulated execution
    price, matching the backtest's no-look-ahead execution convention.
    """

    def __init__(self, config: PaperTradingConfig) -> None:
        self.config = config
        self.cash = config.initial_cash
        self.quantity = Decimal("0")
        self.realized_pnl = Decimal("0")
        self.total_fees = Decimal("0")
        self._entry_price = Decimal("0")
        self._candles: list[MarketBar] = []
        self._pending_signal: TradingSignal | None = None
        self._strategy_version_id: str | None = None
        self._started = False
        self._last_candle_time: datetime | None = None

    @property
    def pending_signal(self) -> TradingSignal | None:
        return self._pending_signal

    @property
    def equity(self) -> Decimal:
        if not self._candles:
            return self.cash
        return self.cash + self.quantity * self._candles[-1].close

    @property
    def position_quantity(self) -> Decimal:
        return self.quantity

    def start(
        self,
        historical_candles: list[MarketBar],
        strategy: Strategy,
        strategy_version_id: str,
    ) -> None:
        """Warm the strategy using history without creating paper fills."""
        self._validate_history(historical_candles)
        if len(historical_candles) < self.config.warmup_candles:
            raise ValueError("not enough historical candles for paper-trading warm-up")
        if not strategy_version_id.strip():
            raise ValueError("strategy_version_id must not be empty")

        self._candles = list(historical_candles[-self.config.warmup_candles :])
        self._strategy_version_id = strategy_version_id
        warmup_signals = strategy.generate_signals(self._candles)
        if len(warmup_signals) != len(self._candles):
            raise ValueError("strategy must return exactly one signal per candle")
        # Warm-up is deliberately non-trading: generated historical signals
        # are discarded so paper mode starts with a flat position.
        self._pending_signal = None
        self._last_candle_time = self._candles[-1].open_time
        self._started = True

    def on_candle(self, candle: MarketBar, strategy: Strategy) -> PaperCandleResult:
        """Process one newly completed candle and simulate any prior signal."""
        if not self._started or self._strategy_version_id is None:
            raise RuntimeError("paper trading must be started before processing candles")
        self._validate_candle(candle)

        order: OrderIntent | None = None
        fill: PaperFill | None = None

        if self._pending_signal is not None:
            order, fill = self._execute_pending(self._pending_signal, candle)
            self._pending_signal = None

        self._candles.append(candle)
        signals = strategy.generate_signals(self._candles)
        if len(signals) != len(self._candles):
            raise ValueError("strategy must return exactly one signal per candle")
        strategy_signal = signals[-1]
        signal = TradingSignal(
            signal_id=uuid4(),
            strategy_version_id=self._strategy_version_id,
            symbol=candle.symbol,
            timeframe=candle.timeframe,
            side=strategy_signal.signal,
            reference_price=strategy_signal.price,
            generated_at=candle.open_time,
            candle_time=candle.open_time,
            reason=strategy_signal.reason,
        )
        if signal.side in {Signal.BUY, Signal.SELL}:
            self._pending_signal = signal

        self._last_candle_time = candle.open_time
        return PaperCandleResult(signal=signal, order=order, fill=fill)

    def _execute_pending(
        self,
        signal: TradingSignal,
        candle: MarketBar,
    ) -> tuple[OrderIntent | None, PaperFill | None]:
        if signal.side == Signal.BUY:
            if self.quantity != 0:
                return None, None
            quantity = self.config.order_quantity
            execution_price = candle.open * (Decimal("1") + self.config.slippage_rate)
            fee = quantity * execution_price * self.config.fee_rate
            required_cash = quantity * execution_price + fee
            if required_cash > self.cash:
                return None, None
        elif signal.side == Signal.SELL:
            if self.quantity == 0:
                return None, None
            quantity = self.quantity
            execution_price = candle.open * (Decimal("1") - self.config.slippage_rate)
            fee = quantity * execution_price * self.config.fee_rate
        else:
            return None, None

        intent = OrderIntent(
            intent_id=uuid4(),
            signal_id=signal.signal_id,
            strategy_version_id=signal.strategy_version_id,
            symbol=signal.symbol,
            timeframe=signal.timeframe,
            side=signal.side,
            quantity=quantity,
            reference_price=signal.reference_price,
            client_order_id=f"paper-{signal.signal_id.hex}",
            reason=signal.reason,
        )

        if signal.side == Signal.BUY:
            self.cash -= quantity * execution_price + fee
            self.quantity += quantity
            self._entry_price = execution_price
        else:
            proceeds = quantity * execution_price - fee
            entry_value = quantity * self._entry_price
            self.cash += proceeds
            self.realized_pnl += proceeds - entry_value
            self.quantity = Decimal("0")
            self._entry_price = Decimal("0")

        self.total_fees += fee

        fill = PaperFill(
            fill_id=uuid4(),
            intent_id=intent.intent_id,
            symbol=candle.symbol,
            side=signal.side,
            quantity=quantity,
            price=execution_price,
            fee=fee,
            executed_at=candle.open_time,
        )
        return intent, fill

    def _validate_history(self, candles: list[MarketBar]) -> None:
        if not candles:
            raise ValueError("historical_candles must not be empty")
        for candle in candles:
            self._validate_market_bar(candle)
        for previous, current in zip(candles[:-1], candles[1:], strict=True):
            if current.open_time <= previous.open_time:
                raise ValueError("historical candles must be strictly ordered by open_time")

    def _validate_candle(self, candle: MarketBar) -> None:
        self._validate_market_bar(candle)
        if self._last_candle_time is not None and candle.open_time <= self._last_candle_time:
            raise ValueError("paper candles must be strictly ordered by open_time")
        if self._candles and (
            candle.symbol != self._candles[-1].symbol
            or candle.timeframe != self._candles[-1].timeframe
        ):
            raise ValueError("paper candle symbol/timeframe must match the warm-up data")

    @staticmethod
    def _validate_market_bar(candle: MarketBar) -> None:
        if not candle.symbol.strip() or not candle.timeframe.strip():
            raise ValueError("candle symbol and timeframe must not be empty")
        if candle.open <= 0 or candle.high <= 0 or candle.low <= 0 or candle.close <= 0:
            raise ValueError("candle prices must be greater than zero")
        if candle.volume < 0:
            raise ValueError("candle volume must not be negative")
