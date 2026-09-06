from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4

from packages.strategies.models import MarketBar, Signal
from packages.trading.paper import OrderIntent


class ExecutionStatus(str, Enum):
    ACCEPTED = "accepted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class ExecutionConfig:
    fill_ratio: Decimal = Decimal("1")
    slippage_rate: Decimal = Decimal("0")
    reject_zero_liquidity: bool = True

    def __post_init__(self) -> None:
        if self.fill_ratio <= 0 or self.fill_ratio > 1:
            raise ValueError("fill_ratio must be greater than zero and at most one")
        if self.slippage_rate < 0 or self.slippage_rate >= 1:
            raise ValueError("slippage_rate must be between zero and one")


@dataclass(frozen=True, slots=True)
class SimulatedOrder:
    simulation_id: UUID
    order_id: str
    status: ExecutionStatus
    requested_quantity: Decimal
    filled_quantity: Decimal
    remaining_quantity: Decimal
    average_fill_price: Decimal | None
    reason: str


@dataclass(frozen=True, slots=True)
class SimulatedFill:
    fill_id: UUID
    simulation_id: UUID
    order_id: str
    symbol: str
    side: Signal
    quantity: Decimal
    price: Decimal
    executed_at: object


class ExecutionSimulator:
    """Deterministic market-order fill simulator with no exchange access."""

    def __init__(self, config: ExecutionConfig | None = None) -> None:
        self.config = config or ExecutionConfig()

    def execute(self, order: OrderIntent, candle: MarketBar) -> tuple[SimulatedOrder, SimulatedFill | None]:
        self._validate(order, candle)
        simulation_id = uuid4()
        if self.config.reject_zero_liquidity and candle.volume <= 0:
            return (
                SimulatedOrder(
                    simulation_id, order.client_order_id, ExecutionStatus.REJECTED,
                    order.quantity, Decimal("0"), order.quantity, None, "market candle has zero volume",
                ),
                None,
            )

        fill_quantity = order.quantity * self.config.fill_ratio
        remaining = order.quantity - fill_quantity
        if order.side == Signal.BUY:
            fill_price = candle.open * (Decimal("1") + self.config.slippage_rate)
        else:
            fill_price = candle.open * (Decimal("1") - self.config.slippage_rate)
        status = ExecutionStatus.FILLED if remaining == 0 else ExecutionStatus.PARTIALLY_FILLED
        fill = SimulatedFill(
            fill_id=uuid4(),
            simulation_id=simulation_id,
            order_id=order.client_order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=fill_quantity,
            price=fill_price,
            executed_at=candle.open_time,
        )
        result = SimulatedOrder(
            simulation_id=simulation_id,
            order_id=order.client_order_id,
            status=status,
            requested_quantity=order.quantity,
            filled_quantity=fill_quantity,
            remaining_quantity=remaining,
            average_fill_price=fill_price,
            reason="simulated market fill",
        )
        return result, fill

    @staticmethod
    def _validate(order: OrderIntent, candle: MarketBar) -> None:
        if order.side not in {Signal.BUY, Signal.SELL}:
            raise ValueError("execution simulator accepts only BUY or SELL orders")
        if order.quantity <= 0:
            raise ValueError("order quantity must be greater than zero")
        if order.symbol.strip().upper() != candle.symbol.strip().upper():
            raise ValueError("order symbol must match execution candle")
        if candle.open <= 0 or candle.volume < 0:
            raise ValueError("execution candle has invalid price or volume")
