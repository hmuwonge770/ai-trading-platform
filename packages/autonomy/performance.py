"""Read-only Testnet performance and execution-quality attribution."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class PerformanceStatus(StrEnum):
    HEALTHY = "healthy"
    REVIEW = "review"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class ExecutionObservation:
    """One completed Testnet execution observation."""

    order_id: str
    symbol: str
    expected_price: Decimal
    fill_price: Decimal
    expected_quantity: Decimal
    filled_quantity: Decimal
    submitted_at: int
    completed_at: int

    def __post_init__(self) -> None:
        if not self.order_id.strip() or not self.symbol.strip():
            raise ValueError("order_id and symbol must not be empty")
        if self.expected_price <= 0 or self.fill_price <= 0:
            raise ValueError("prices must be positive")
        if self.expected_quantity <= 0 or self.filled_quantity < 0:
            raise ValueError("quantities are invalid")
        if self.filled_quantity > self.expected_quantity:
            raise ValueError("filled quantity must not exceed expected quantity")
        if self.submitted_at <= 0 or self.completed_at < self.submitted_at:
            raise ValueError("execution timestamps are invalid")


@dataclass(frozen=True, slots=True)
class PerformancePolicy:
    max_slippage_bps: Decimal = Decimal("50")
    max_fill_shortfall_ratio: Decimal = Decimal("0.10")

    def __post_init__(self) -> None:
        if self.max_slippage_bps < 0:
            raise ValueError("max_slippage_bps must be non-negative")
        if not 0 <= self.max_fill_shortfall_ratio <= 1:
            raise ValueError("max_fill_shortfall_ratio must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class PerformanceReport:
    status: PerformanceStatus
    observations: int
    average_slippage_bps: Decimal
    fill_rate: Decimal
    total_expected_notional: Decimal
    total_filled_notional: Decimal
    max_slippage_bps: Decimal
    reasons: tuple[str, ...]

    @property
    def healthy(self) -> bool:
        return self.status is PerformanceStatus.HEALTHY


class AutonomousTestnetPerformanceMonitor:
    """Attribute execution quality without submitting or modifying orders."""

    def __init__(self, *, policy: PerformancePolicy | None = None) -> None:
        self.policy = policy or PerformancePolicy()

    def assess(self, observations: tuple[ExecutionObservation, ...]) -> PerformanceReport:
        if not observations:
            return PerformanceReport(
                PerformanceStatus.UNAVAILABLE, 0, Decimal("0"), Decimal("0"),
                Decimal("0"), Decimal("0"), Decimal("0"), ("no_observations",),
            )

        slippages: list[Decimal] = []
        expected_notional = Decimal("0")
        filled_notional = Decimal("0")
        filled_quantity = Decimal("0")
        expected_quantity = Decimal("0")
        reasons: list[str] = []

        for observation in observations:
            slippage_bps = ((observation.fill_price - observation.expected_price) / observation.expected_price) * Decimal("10000")
            slippages.append(abs(slippage_bps))
            expected_notional += observation.expected_price * observation.expected_quantity
            filled_notional += observation.fill_price * observation.filled_quantity
            expected_quantity += observation.expected_quantity
            filled_quantity += observation.filled_quantity

        average_slippage = sum(slippages, Decimal("0")) / Decimal(len(slippages))
        max_slippage = max(slippages)
        fill_rate = filled_quantity / expected_quantity if expected_quantity else Decimal("0")

        if max_slippage > self.policy.max_slippage_bps:
            reasons.append("slippage_limit_exceeded")
        shortfall = Decimal("1") - fill_rate
        if shortfall > self.policy.max_fill_shortfall_ratio:
            reasons.append("fill_rate_limit_exceeded")

        return PerformanceReport(
            PerformanceStatus.REVIEW if reasons else PerformanceStatus.HEALTHY,
            len(observations), average_slippage, fill_rate,
            expected_notional, filled_notional, max_slippage, tuple(reasons),
        )
