"""Fail-closed recovery decisions for autonomous position state."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class PositionRecoveryStatus(StrEnum):
    MATCHED = "matched"
    MISSING = "missing"
    ORPHANED = "orphaned"
    QUANTITY_MISMATCH = "quantity_mismatch"
    STALE = "stale"
    UNAVAILABLE = "unavailable"


class PositionRecoveryAction(StrEnum):
    CONTINUE = "continue"
    RECONCILE = "reconcile"
    HALT = "halt"


@dataclass(frozen=True, slots=True)
class ExpectedPosition:
    symbol: str
    quantity: Decimal

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol must not be empty")
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")


@dataclass(frozen=True, slots=True)
class ObservedPosition:
    symbol: str
    quantity: Decimal

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol must not be empty")
        if self.quantity < 0:
            raise ValueError("quantity must be non-negative")


@dataclass(frozen=True, slots=True)
class PositionRecoveryPolicy:
    max_snapshot_age_seconds: int = 30
    quantity_tolerance: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if self.max_snapshot_age_seconds <= 0:
            raise ValueError("max_snapshot_age_seconds must be positive")
        if self.quantity_tolerance < 0:
            raise ValueError("quantity_tolerance must be non-negative")


@dataclass(frozen=True, slots=True)
class PositionRecoveryReport:
    status: PositionRecoveryStatus
    action: PositionRecoveryAction
    healthy: bool
    reasons: tuple[str, ...]
    observed_at: int | None = None


class AutonomousPositionRecovery:
    """Compare expected and observed positions without trading authority.

    Any missing, orphaned, mismatched, stale, or unavailable state requires
    reconciliation or a halt. This component never submits, cancels, amends,
    or retries orders and never changes capital or risk policy.
    """

    def __init__(self, *, policy: PositionRecoveryPolicy | None = None) -> None:
        self.policy = policy or PositionRecoveryPolicy()

    def assess(
        self,
        expected: tuple[ExpectedPosition, ...],
        observed: tuple[ObservedPosition, ...],
        *,
        observed_at: int,
        now: int,
    ) -> PositionRecoveryReport:
        if now <= 0 or observed_at <= 0:
            return self._unsafe(PositionRecoveryStatus.UNAVAILABLE, ("invalid_timestamp",))
        age = now - observed_at
        if age < 0:
            return self._unsafe(PositionRecoveryStatus.STALE, ("snapshot_from_future",), observed_at)
        if age > self.policy.max_snapshot_age_seconds:
            return self._unsafe(PositionRecoveryStatus.STALE, ("snapshot_stale",), observed_at)

        expected_map = {item.symbol: item for item in expected}
        observed_map = {item.symbol: item for item in observed}
        reasons: list[str] = []

        for symbol, position in expected_map.items():
            actual = observed_map.get(symbol)
            if actual is None:
                reasons.append(f"missing_position:{symbol}")
                continue
            if abs(actual.quantity - position.quantity) > self.policy.quantity_tolerance:
                reasons.append(f"quantity_mismatch:{symbol}")

        for symbol in observed_map.keys() - expected_map.keys():
            if observed_map[symbol].quantity > self.policy.quantity_tolerance:
                reasons.append(f"orphaned_position:{symbol}")

        if reasons:
            return self._unsafe(PositionRecoveryStatus.QUANTITY_MISMATCH if any("quantity_mismatch" in reason for reason in reasons) else (PositionRecoveryStatus.MISSING if any("missing_position" in reason for reason in reasons) else PositionRecoveryStatus.ORPHANED), tuple(reasons), observed_at)

        return PositionRecoveryReport(PositionRecoveryStatus.MATCHED, PositionRecoveryAction.CONTINUE, True, (), observed_at)

    @staticmethod
    def _unsafe(
        status: PositionRecoveryStatus,
        reasons: tuple[str, ...],
        observed_at: int | None = None,
    ) -> PositionRecoveryReport:
        return PositionRecoveryReport(status, PositionRecoveryAction.HALT, False, reasons, observed_at)
