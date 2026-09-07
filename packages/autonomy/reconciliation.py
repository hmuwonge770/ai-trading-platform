"""Fail-closed reconciliation of autonomous expectations with Testnet state."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Protocol

from packages.autonomy.recovery import AutonomousRecoveryEngine, RecoveryAction, RecoveryEvent


class ReconciliationStatus(StrEnum):
    HEALTHY = "healthy"
    MISMATCH = "mismatch"
    STALE = "stale"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class ExpectedOrder:
    client_order_id: str
    symbol: str
    quantity: Decimal
    status: str

    def __post_init__(self) -> None:
        if not self.client_order_id.strip():
            raise ValueError("client_order_id must not be empty")
        if not self.symbol.strip():
            raise ValueError("symbol must not be empty")
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if not self.status.strip():
            raise ValueError("status must not be empty")


@dataclass(frozen=True, slots=True)
class ObservedOrder:
    client_order_id: str
    symbol: str
    quantity: Decimal
    status: str


@dataclass(frozen=True, slots=True)
class ExchangeSnapshot:
    observed_at: int
    orders: tuple[ObservedOrder, ...]

    def __post_init__(self) -> None:
        if self.observed_at <= 0:
            raise ValueError("observed_at must be positive")


class TestnetStateProvider(Protocol):
    def snapshot(self) -> ExchangeSnapshot: ...


@dataclass(frozen=True, slots=True)
class ReconciliationPolicy:
    max_snapshot_age_seconds: int = 30
    quantity_tolerance: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if self.max_snapshot_age_seconds <= 0:
            raise ValueError("max_snapshot_age_seconds must be positive")
        if self.quantity_tolerance < 0:
            raise ValueError("quantity_tolerance must be non-negative")


@dataclass(frozen=True, slots=True)
class ReconciliationResult:
    status: ReconciliationStatus
    healthy: bool
    reasons: tuple[str, ...]
    recovery_action: RecoveryAction
    observed_at: int | None = None


class AutonomousTestnetReconciler:
    """Compare expected Testnet state with an injected exchange snapshot.

    Reconciliation is read-only. It never submits, cancels, or amends orders.
    Any uncertainty is fail-closed and routed to the existing recovery engine.
    """

    def __init__(
        self,
        provider: TestnetStateProvider,
        *,
        policy: ReconciliationPolicy | None = None,
        recovery_engine: AutonomousRecoveryEngine | None = None,
    ) -> None:
        self.provider = provider
        self.policy = policy or ReconciliationPolicy()
        self.recovery_engine = recovery_engine or AutonomousRecoveryEngine()

    def reconcile(
        self,
        expected_orders: tuple[ExpectedOrder, ...],
        *,
        now: int,
    ) -> ReconciliationResult:
        if now <= 0:
            return self._unsafe(ReconciliationStatus.UNAVAILABLE, ("invalid_current_time",))

        try:
            snapshot = self.provider.snapshot()
        except Exception:
            return self._unavailable()

        age = now - snapshot.observed_at
        if age < 0:
            return self._unsafe(ReconciliationStatus.STALE, ("snapshot_from_future",), snapshot.observed_at)
        if age > self.policy.max_snapshot_age_seconds:
            return self._unsafe(ReconciliationStatus.STALE, ("snapshot_stale",), snapshot.observed_at)

        expected = {order.client_order_id: order for order in expected_orders}
        observed = {order.client_order_id: order for order in snapshot.orders}
        reasons: list[str] = []

        for order_id, order in expected.items():
            actual = observed.get(order_id)
            if actual is None:
                reasons.append(f"missing_order:{order_id}")
                continue
            if actual.symbol != order.symbol:
                reasons.append(f"symbol_mismatch:{order_id}")
            if abs(actual.quantity - order.quantity) > self.policy.quantity_tolerance:
                reasons.append(f"quantity_mismatch:{order_id}")
            if actual.status != order.status:
                reasons.append(f"status_mismatch:{order_id}")

        for order_id in observed.keys() - expected.keys():
            reasons.append(f"unknown_order:{order_id}")

        if reasons:
            return self._unsafe(ReconciliationStatus.MISMATCH, tuple(reasons), snapshot.observed_at)

        recovery = self.recovery_engine.observe(RecoveryEvent.SUCCESS)
        return ReconciliationResult(
            ReconciliationStatus.HEALTHY,
            True,
            (),
            recovery.action,
            snapshot.observed_at,
        )

    def reset_recovery_after_success(self) -> ReconciliationResult:
        decision = self.recovery_engine.reset_after_reconciliation()
        return ReconciliationResult(
            ReconciliationStatus.HEALTHY,
            True,
            (),
            decision.action,
        )

    def _unavailable(self) -> ReconciliationResult:
        return self._unsafe(ReconciliationStatus.UNAVAILABLE, ("exchange_state_unavailable",))

    def _unsafe(
        self,
        status: ReconciliationStatus,
        reasons: tuple[str, ...],
        observed_at: int | None = None,
    ) -> ReconciliationResult:
        recovery = self.recovery_engine.observe(RecoveryEvent.RECONCILIATION_MISMATCH)
        return ReconciliationResult(status, False, reasons, recovery.action, observed_at)
