from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from packages.portfolio import PortfolioSnapshot
from packages.strategies.models import Signal
from packages.trading.paper import OrderIntent


class RiskReason(str, Enum):
    APPROVED = "approved"
    INVALID_ORDER = "invalid_order"
    ORDER_NOTIONAL_LIMIT = "order_notional_limit"
    POSITION_NOTIONAL_LIMIT = "position_notional_limit"
    TOTAL_EXPOSURE_LIMIT = "total_exposure_limit"
    DAILY_LOSS_LIMIT = "daily_loss_limit"
    INSUFFICIENT_CASH = "insufficient_cash"
    INSUFFICIENT_POSITION = "insufficient_position"


@dataclass(frozen=True, slots=True)
class RiskLimits:
    max_order_notional: Decimal
    max_position_notional: Decimal
    max_total_exposure: Decimal
    max_daily_loss: Decimal
    min_cash_after_order: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        for name, value in (
            ("max_order_notional", self.max_order_notional),
            ("max_position_notional", self.max_position_notional),
            ("max_total_exposure", self.max_total_exposure),
            ("max_daily_loss", self.max_daily_loss),
        ):
            if value <= 0:
                raise ValueError(f"{name} must be greater than zero")
        if self.min_cash_after_order < 0:
            raise ValueError("min_cash_after_order must not be negative")


@dataclass(frozen=True, slots=True)
class RiskContext:
    portfolio: PortfolioSnapshot
    current_price: Decimal
    total_exposure: Decimal
    daily_realized_pnl: Decimal


@dataclass(frozen=True, slots=True)
class RiskDecision:
    approved: bool
    reason: RiskReason
    message: str
    order_id: str
    order_notional: Decimal
    projected_position_notional: Decimal
    projected_total_exposure: Decimal


class RiskGateway:
    """Deterministic pre-trade risk gate with no exchange access."""

    def __init__(self, limits: RiskLimits) -> None:
        self.limits = limits

    def evaluate(self, order: OrderIntent, context: RiskContext) -> RiskDecision:
        quantity = order.quantity
        price = context.current_price
        order_notional = quantity * price
        position = next((p for p in context.portfolio.positions if p.symbol == order.symbol), None)
        current_quantity = position.quantity if position else Decimal("0")

        if order.side == Signal.BUY:
            projected_quantity = current_quantity + quantity
            projected_total_exposure = context.total_exposure + order_notional
        elif order.side == Signal.SELL:
            projected_quantity = current_quantity - quantity
            projected_total_exposure = max(Decimal("0"), context.total_exposure - order_notional)
        else:
            return self._decision(
                False, RiskReason.INVALID_ORDER, "risk gateway accepts only BUY or SELL orders",
                order, order_notional, Decimal("0"), context.total_exposure,
            )

        projected_position_notional = projected_quantity * price
        if quantity <= 0 or price <= 0 or not order.symbol.strip():
            return self._decision(
                False, RiskReason.INVALID_ORDER, "order quantity, price and symbol must be valid",
                order, order_notional, projected_position_notional, projected_total_exposure,
            )
        if order.side == Signal.SELL and projected_quantity < 0:
            return self._decision(
                False, RiskReason.INSUFFICIENT_POSITION, "sell quantity exceeds the current position",
                order, order_notional, projected_position_notional, projected_total_exposure,
            )
        if order_notional > self.limits.max_order_notional:
            return self._decision(
                False, RiskReason.ORDER_NOTIONAL_LIMIT, "order notional exceeds the configured limit",
                order, order_notional, projected_position_notional, projected_total_exposure,
            )
        if order.side == Signal.BUY and projected_position_notional > self.limits.max_position_notional:
            return self._decision(
                False, RiskReason.POSITION_NOTIONAL_LIMIT, "projected position exceeds the configured limit",
                order, order_notional, projected_position_notional, projected_total_exposure,
            )
        if projected_total_exposure > self.limits.max_total_exposure:
            return self._decision(
                False, RiskReason.TOTAL_EXPOSURE_LIMIT, "projected exposure exceeds the configured limit",
                order, order_notional, projected_position_notional, projected_total_exposure,
            )
        if context.portfolio.available_cash < 0 or context.portfolio.reserved_cash < 0:
            return self._decision(
                False, RiskReason.INSUFFICIENT_CASH, "portfolio cash balances cannot be negative",
                order, order_notional, projected_position_notional, projected_total_exposure,
            )
        if order.side == Signal.BUY:
            required_cash = order_notional + self.limits.min_cash_after_order
            if context.portfolio.available_cash < required_cash:
                return self._decision(
                    False, RiskReason.INSUFFICIENT_CASH, "order would violate the minimum remaining cash requirement",
                    order, order_notional, projected_position_notional, projected_total_exposure,
                )
            if context.daily_realized_pnl <= -self.limits.max_daily_loss:
                return self._decision(
                    False, RiskReason.DAILY_LOSS_LIMIT, "daily loss limit blocks new risk",
                    order, order_notional, projected_position_notional, projected_total_exposure,
                )

        return self._decision(
            True, RiskReason.APPROVED, "order passed deterministic pre-trade risk checks",
            order, order_notional, projected_position_notional, projected_total_exposure,
        )

    @staticmethod
    def _decision(
        approved: bool,
        reason: RiskReason,
        message: str,
        order: OrderIntent,
        order_notional: Decimal,
        projected_position_notional: Decimal,
        projected_total_exposure: Decimal,
    ) -> RiskDecision:
        return RiskDecision(
            approved=approved,
            reason=reason,
            message=message,
            order_id=order.client_order_id,
            order_notional=order_notional,
            projected_position_notional=projected_position_notional,
            projected_total_exposure=projected_total_exposure,
        )
