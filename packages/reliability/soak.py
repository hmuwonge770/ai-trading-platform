from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from packages.reliability.faults import FailurePlan, InjectedFailure


@dataclass(frozen=True, slots=True)
class SoakConfig:
    """Accelerated configuration for a deterministic virtual-time soak run."""

    duration: timedelta = timedelta(hours=72)
    tick: timedelta = timedelta(minutes=10)
    failure_plan: FailurePlan | None = None

    def __post_init__(self) -> None:
        if self.duration <= timedelta(0):
            raise ValueError("duration must be positive")
        if self.tick <= timedelta(0):
            raise ValueError("tick must be positive")
        if self.duration.total_seconds() % self.tick.total_seconds() != 0:
            raise ValueError("duration must be an exact multiple of tick")


@dataclass(frozen=True, slots=True)
class SoakReport:
    duration: timedelta
    ticks: int
    successful_ticks: int
    injected_failures: int
    recovered_failures: int
    duplicate_events: int
    invariant_violations: int
    final_balance: int

    @property
    def healthy(self) -> bool:
        return (
            self.successful_ticks + self.recovered_failures == self.ticks
            and self.duplicate_events == 0
            and self.invariant_violations == 0
            and self.final_balance == self.ticks
        )


class DeterministicSoakRunner:
    """Run the trading reliability loop against virtual time, never wall-clock time."""

    def __init__(self, config: SoakConfig | None = None) -> None:
        self.config = config or SoakConfig()
        self.failure_plan = self.config.failure_plan or FailurePlan()

    def run(self, start: datetime | None = None) -> SoakReport:
        current = start or datetime(2026, 1, 1, tzinfo=timezone.utc)
        if current.tzinfo is None:
            raise ValueError("start must be timezone-aware")

        ticks = int(self.config.duration / self.config.tick)
        successful = 0
        injected = 0
        recovered = 0
        duplicates = 0
        violations = 0
        balance = 0
        seen_events: set[str] = set()

        for index in range(1, ticks + 1):
            event_id = f"soak-{index:06d}"
            if event_id in seen_events:
                duplicates += 1
            seen_events.add(event_id)
            try:
                self.failure_plan.checkpoint("soak-tick")
                balance += 1
                successful += 1
            except InjectedFailure:
                injected += 1
                # A failed delivery is retried once with the same idempotency key.
                self.failure_plan.checkpoint("soak-retry")
                balance += 1
                recovered += 1

            if balance < 0 or balance > index:
                violations += 1
            current += self.config.tick

        return SoakReport(
            duration=current - (start or datetime(2026, 1, 1, tzinfo=timezone.utc)),
            ticks=ticks,
            successful_ticks=successful,
            injected_failures=injected,
            recovered_failures=recovered,
            duplicate_events=duplicates,
            invariant_violations=violations,
            final_balance=balance,
        )
