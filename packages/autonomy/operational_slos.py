"""Deterministic operational SLO and capacity contracts for autonomous trading."""
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from enum import StrEnum


class SLOStatus(StrEnum):
    HEALTHY = "healthy"
    AT_RISK = "at_risk"
    BREACHED = "breached"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class OperationalSLOPolicy:
    min_availability_percent: Decimal = Decimal("99")
    max_decision_latency_ms: Decimal = Decimal("1000")
    max_reconciliation_latency_ms: Decimal = Decimal("5000")
    max_error_rate_percent: Decimal = Decimal("1")
    max_queue_depth: int = 1000
    max_concurrent_workers: int = 32
    min_capacity_headroom_percent: Decimal = Decimal("20")
    observation_window_seconds: int = 300

    def __post_init__(self) -> None:
        decimals = (self.min_availability_percent, self.max_decision_latency_ms, self.max_reconciliation_latency_ms, self.max_error_rate_percent, self.min_capacity_headroom_percent)
        if any(not x.is_finite() for x in decimals):
            raise ValueError("SLO policy values must be finite")
        if any(x < 0 for x in decimals) or self.observation_window_seconds <= 0 or self.max_queue_depth < 0 or self.max_concurrent_workers <= 0:
            raise ValueError("SLO policy values must be non-negative and bounded")
        if self.min_availability_percent > 100 or self.max_error_rate_percent > 100 or self.min_capacity_headroom_percent > 100:
            raise ValueError("percentage policy values exceed 100")


@dataclass(frozen=True, slots=True)
class OperationalObservation:
    availability_percent: Decimal
    decision_latency_ms: Decimal
    reconciliation_latency_ms: Decimal
    error_rate_percent: Decimal
    queue_depth: int
    active_workers: int
    worker_capacity: int
    window: timedelta

    def __post_init__(self) -> None:
        values = (self.availability_percent, self.decision_latency_ms, self.reconciliation_latency_ms, self.error_rate_percent)
        if any(not x.is_finite() for x in values):
            raise ValueError("operational observations must be finite")
        if any(x < 0 for x in values) or self.queue_depth < 0 or self.active_workers < 0 or self.worker_capacity <= 0 or self.window.total_seconds() <= 0:
            raise ValueError("operational observations must be valid and non-negative")
        if self.availability_percent > 100 or self.error_rate_percent > 100 or self.active_workers > self.worker_capacity:
            raise ValueError("operational observation is out of bounds")

    @property
    def capacity_headroom_percent(self) -> Decimal:
        return (Decimal(self.worker_capacity - self.active_workers) / Decimal(self.worker_capacity)) * Decimal("100")

    @property
    def capacity_utilization_percent(self) -> Decimal:
        return (Decimal(self.active_workers) / Decimal(self.worker_capacity)) * Decimal("100")
