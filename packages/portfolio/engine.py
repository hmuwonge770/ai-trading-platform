from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class PortfolioConfig:
    """Configuration for one spot portfolio account."""

    base_currency: str
    initial_cash: Decimal

    def __post_init__(self) -> None:
        currency = self.base_currency.strip().upper()
        if not currency:
            raise ValueError("base_currency must not be empty")
        if self.initial_cash < 0:
            raise ValueError("initial_cash must not be negative")
        object.__setattr__(self, "base_currency", currency)


@dataclass(frozen=True, slots=True)
class MoneyMovement:
    """Immutable record describing a portfolio cash movement."""

    movement_id: UUID
    asset: str
    movement_type: str
    amount: Decimal
    reference: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class PositionSnapshot:
    symbol: str
    quantity: Decimal
    average_entry_price: Decimal
    realized_pnl: Decimal


@dataclass(frozen=True, slots=True)
class PortfolioSnapshot:
    base_currency: str
    available_cash: Decimal
    reserved_cash: Decimal
    positions: tuple[PositionSnapshot, ...]
    realized_pnl: Decimal
    total_fees: Decimal


class PortfolioEngine:
    """Deterministic spot portfolio state.

    This is the money/position boundary used by later execution and risk
    stages. It does not know about exchanges, network calls, or order routing.
    Every state transition validates sufficient funds/assets before mutating
    state. Money movements are append-only and reference-keyed by callers.
    """

    def __init__(self, config: PortfolioConfig) -> None:
        self.config = config
        self._available_cash = config.initial_cash
        self._reserved_cash = Decimal("0")
        self._positions: dict[str, PositionSnapshot] = {}
        self._movements: list[MoneyMovement] = []
        self._movement_references: set[str] = set()
        self._realized_pnl = Decimal("0")
        self._total_fees = Decimal("0")

    @property
    def available_cash(self) -> Decimal:
        return self._available_cash

    @property
    def reserved_cash(self) -> Decimal:
        return self._reserved_cash

    @property
    def realized_pnl(self) -> Decimal:
        return self._realized_pnl

    @property
    def total_fees(self) -> Decimal:
        return self._total_fees

    @property
    def movements(self) -> tuple[MoneyMovement, ...]:
        return tuple(self._movements)

    def snapshot(self) -> PortfolioSnapshot:
        return PortfolioSnapshot(
            base_currency=self.config.base_currency,
            available_cash=self._available_cash,
            reserved_cash=self._reserved_cash,
            positions=tuple(self._positions[key] for key in sorted(self._positions)),
            realized_pnl=self._realized_pnl,
            total_fees=self._total_fees,
        )

    def deposit(self, amount: Decimal, reference: str) -> MoneyMovement:
        self._validate_positive(amount, "deposit amount")
        movement = self._record_movement("deposit", amount, reference)
        self._available_cash += amount
        return movement

    def withdraw(self, amount: Decimal, reference: str) -> MoneyMovement:
        self._validate_positive(amount, "withdrawal amount")
        if amount > self._available_cash:
            raise ValueError("insufficient available cash")
        movement = self._record_movement("withdrawal", amount, reference)
        self._available_cash -= amount
        return movement

    def reserve_cash(self, amount: Decimal) -> None:
        self._validate_positive(amount, "reserve amount")
        if amount > self._available_cash:
            raise ValueError("insufficient available cash to reserve")
        self._available_cash -= amount
        self._reserved_cash += amount

    def release_cash(self, amount: Decimal) -> None:
        self._validate_positive(amount, "release amount")
        if amount > self._reserved_cash:
            raise ValueError("cannot release more cash than reserved")
        self._reserved_cash -= amount
        self._available_cash += amount

    def buy(
        self,
        symbol: str,
        quantity: Decimal,
        price: Decimal,
        fee: Decimal = Decimal("0"),
    ) -> PositionSnapshot:
        symbol = self._normalize_symbol(symbol)
        self._validate_trade(quantity, price, fee)
        total = quantity * price + fee
        if total > self._available_cash:
            raise ValueError("insufficient available cash for purchase")

        self._available_cash -= total
        self._total_fees += fee
        current = self._positions.get(symbol)
        if current is None:
            position = PositionSnapshot(symbol, quantity, price, Decimal("0"))
        else:
            new_quantity = current.quantity + quantity
            weighted_price = (
                current.quantity * current.average_entry_price + quantity * price
            ) / new_quantity
            position = PositionSnapshot(symbol, new_quantity, weighted_price, current.realized_pnl)
        self._positions[symbol] = position
        return position

    def sell(
        self,
        symbol: str,
        quantity: Decimal,
        price: Decimal,
        fee: Decimal = Decimal("0"),
    ) -> PositionSnapshot:
        symbol = self._normalize_symbol(symbol)
        self._validate_trade(quantity, price, fee)
        current = self._positions.get(symbol)
        if current is None or quantity > current.quantity:
            raise ValueError("insufficient position quantity for sale")

        proceeds = quantity * price - fee
        realized = quantity * (price - current.average_entry_price) - fee
        self._available_cash += proceeds
        self._realized_pnl += realized
        self._total_fees += fee
        remaining = current.quantity - quantity
        if remaining == 0:
            position = PositionSnapshot(symbol, Decimal("0"), Decimal("0"), current.realized_pnl + realized)
        else:
            position = PositionSnapshot(symbol, remaining, current.average_entry_price, current.realized_pnl + realized)
        self._positions[symbol] = position
        return position

    def charge_fee(self, amount: Decimal, reference: str) -> MoneyMovement:
        self._validate_positive(amount, "fee amount")
        if amount > self._available_cash:
            raise ValueError("insufficient available cash for fee")
        movement = self._record_movement("fee", amount, reference)
        self._available_cash -= amount
        self._total_fees += amount
        return movement

    def _record_movement(self, movement_type: str, amount: Decimal, reference: str) -> MoneyMovement:
        reference = reference.strip()
        if not reference:
            raise ValueError("movement reference must not be empty")
        if reference in self._movement_references:
            raise ValueError("movement reference already exists")
        movement = MoneyMovement(
            movement_id=uuid4(),
            asset=self.config.base_currency,
            movement_type=movement_type,
            amount=amount,
            reference=reference,
            created_at=datetime.now(timezone.utc),
        )
        self._movement_references.add(reference)
        self._movements.append(movement)
        return movement

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        value = symbol.strip().upper()
        if not value:
            raise ValueError("symbol must not be empty")
        return value

    @staticmethod
    def _validate_positive(amount: Decimal, name: str) -> None:
        if amount <= 0:
            raise ValueError(f"{name} must be greater than zero")

    @classmethod
    def _validate_trade(cls, quantity: Decimal, price: Decimal, fee: Decimal) -> None:
        cls._validate_positive(quantity, "quantity")
        cls._validate_positive(price, "price")
        if fee < 0:
            raise ValueError("fee must not be negative")
