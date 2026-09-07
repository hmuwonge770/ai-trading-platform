"""Fail-closed Testnet balance and position accounting reconciliation."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Protocol

from packages.autonomy.recovery import AutonomousRecoveryEngine, RecoveryAction, RecoveryEvent


class AccountingStatus(StrEnum):
    HEALTHY = "healthy"
    MISMATCH = "mismatch"
    STALE = "stale"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class ExpectedBalance:
    asset: str
    free: Decimal
    locked: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if not self.asset.strip():
            raise ValueError("asset must not be empty")
        if self.free < 0 or self.locked < 0:
            raise ValueError("balance quantities must be non-negative")


@dataclass(frozen=True, slots=True)
class ObservedBalance:
    asset: str
    free: Decimal
    locked: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if not self.asset.strip():
            raise ValueError("asset must not be empty")
        if self.free < 0 or self.locked < 0:
            raise ValueError("balance quantities must be non-negative")


@dataclass(frozen=True, slots=True)
class ExpectedPosition:
    symbol: str
    quantity: Decimal

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol must not be empty")
        if self.quantity < 0:
            raise ValueError("position quantity must be non-negative")


@dataclass(frozen=True, slots=True)
class ObservedPosition:
    symbol: str
    quantity: Decimal

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol must not be empty")
        if self.quantity < 0:
            raise ValueError("position quantity must be non-negative")


@dataclass(frozen=True, slots=True)
class AccountingSnapshot:
    observed_at: int
    balances: tuple[ObservedBalance, ...]
    positions: tuple[ObservedPosition, ...]

    def __post_init__(self) -> None:
        if self.observed_at <= 0:
            raise ValueError("observed_at must be positive")


class TestnetAccountingProvider(Protocol):
    def snapshot(self) -> AccountingSnapshot: ...


@dataclass(frozen=True, slots=True)
class AccountingPolicy:
    max_snapshot_age_seconds: int = 30
    quantity_tolerance: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if self.max_snapshot_age_seconds <= 0:
            raise ValueError("max_snapshot_age_seconds must be positive")
        if self.quantity_tolerance < 0:
            raise ValueError("quantity_tolerance must be non-negative")


@dataclass(frozen=True, slots=True)
class AccountingResult:
    status: AccountingStatus
    healthy: bool
    reasons: tuple[str, ...]
    recovery_action: RecoveryAction
    observed_at: int | None = None


class AutonomousTestnetAccountingReconciler:
    """Compare local accounting expectations with read-only Testnet state."""

    def __init__(
        self,
        provider: TestnetAccountingProvider,
        *,
        policy: AccountingPolicy | None = None,
        recovery_engine: AutonomousRecoveryEngine | None = None,
    ) -> None:
        self.provider = provider
        self.policy = policy or AccountingPolicy()
        self.recovery_engine = recovery_engine or AutonomousRecoveryEngine()

    def reconcile(
        self,
        expected_balances: tuple[ExpectedBalance, ...],
        expected_positions: tuple[ExpectedPosition, ...],
        *,
        now: int,
    ) -> AccountingResult:
        if now <= 0:
            return self._unsafe(AccountingStatus.UNAVAILABLE, ("invalid_current_time",))

        try:
            snapshot = self.provider.snapshot()
        except Exception:
            return self._unsafe(AccountingStatus.UNAVAILABLE, ("accounting_state_unavailable",))

        age = now - snapshot.observed_at
        if age < 0:
            return self._unsafe(AccountingStatus.STALE, ("snapshot_from_future",), snapshot.observed_at)
        if age > self.policy.max_snapshot_age_seconds:
            return self._unsafe(AccountingStatus.STALE, ("snapshot_stale",), snapshot.observed_at)

        reasons: list[str] = []
        expected_b = {item.asset: item for item in expected_balances}
        observed_b = {item.asset: item for item in snapshot.balances}
        expected_p = {item.symbol: item for item in expected_positions}
        observed_p = {item.symbol: item for item in snapshot.positions}

        for asset, expected in expected_b.items():
            actual = observed_b.get(asset)
            if actual is None:
                reasons.append(f"missing_balance:{asset}")
                continue
            if abs(actual.free - expected.free) > self.policy.quantity_tolerance:
                reasons.append(f"free_balance_mismatch:{asset}")
            if abs(actual.locked - expected.locked) > self.policy.quantity_tolerance:
                reasons.append(f"locked_balance_mismatch:{asset}")
        for asset in observed_b.keys() - expected_b.keys():
            reasons.append(f"unexpected_balance:{asset}")

        for symbol, expected in expected_p.items():
            actual = observed_p.get(symbol)
            if actual is None:
                reasons.append(f"missing_position:{symbol}")
                continue
            if abs(actual.quantity - expected.quantity) > self.policy.quantity_tolerance:
                reasons.append(f"position_quantity_mismatch:{symbol}")
        for symbol in observed_p.keys() - expected_p.keys():
            reasons.append(f"unexpected_position:{symbol}")

        if reasons:
            return self._unsafe(AccountingStatus.MISMATCH, tuple(reasons), snapshot.observed_at)

        recovery = self.recovery_engine.observe(RecoveryEvent.SUCCESS)
        return AccountingResult(AccountingStatus.HEALTHY, True, (), recovery.action, snapshot.observed_at)

    def reset_recovery_after_success(self) -> AccountingResult:
        decision = self.recovery_engine.reset_after_reconciliation()
        return AccountingResult(AccountingStatus.HEALTHY, True, (), decision.action)

    def _unsafe(
        self,
        status: AccountingStatus,
        reasons: tuple[str, ...],
        observed_at: int | None = None,
    ) -> AccountingResult:
        recovery = self.recovery_engine.observe(RecoveryEvent.RECONCILIATION_MISMATCH)
        return AccountingResult(status, False, reasons, recovery.action, observed_at)
