"""Continuous, fail-closed market decision loop for autonomous trading."""

from __future__ import annotations

from collections import deque
from collections.abc import AsyncIterable, Awaitable, Callable
from dataclasses import dataclass
from time import time

from packages.autonomy.control import AutonomousControl
from packages.autonomy.decision import AutonomousDecisionEngine, Decision, MarketSnapshot


@dataclass(frozen=True, slots=True)
class MarketEvent:
    """A normalized, completed market observation ready for evaluation."""

    event_id: str
    snapshot: MarketSnapshot
    closed: bool
    observed_at: float

    def __post_init__(self) -> None:
        if not self.event_id.strip():
            raise ValueError("event_id is required")
        if self.observed_at <= 0:
            raise ValueError("observed_at must be positive")


DecisionSink = Callable[[Decision], Awaitable[None]]
ControlProvider = Callable[[], AutonomousControl]


class AutonomousSignalLoop:
    """Evaluate completed market events while enforcing autonomy controls.

    The loop is deliberately separated from exchange transport. A market-data
    adapter owns reconnects and normalization; this component owns freshness,
    idempotency, decision evaluation, and the fail-closed control boundary.
    """

    def __init__(
        self,
        control: ControlProvider,
        engine: AutonomousDecisionEngine | None = None,
        *,
        max_event_age_seconds: float = 30.0,
        dedupe_capacity: int = 10_000,
        clock: Callable[[], float] = time,
    ) -> None:
        if max_event_age_seconds <= 0:
            raise ValueError("max_event_age_seconds must be positive")
        if dedupe_capacity <= 0:
            raise ValueError("dedupe_capacity must be positive")
        self.control = control
        self.engine = engine or AutonomousDecisionEngine()
        self.max_event_age_seconds = max_event_age_seconds
        self._seen = set[str]()
        self._seen_order: deque[str] = deque(maxlen=dedupe_capacity)
        self._clock = clock

    def process(self, event: MarketEvent) -> Decision | None:
        """Process one event, returning a decision only when safe to evaluate."""
        if not event.closed:
            return None
        if event.event_id in self._seen:
            return None
        if self._clock() - event.observed_at > self.max_event_age_seconds:
            return None
        if self._clock() < event.observed_at:
            return None
        if not self.control().can_run():
            return None

        decision = self.engine.evaluate(event.snapshot)
        self._remember(event.event_id)
        return decision

    async def run(
        self,
        source: AsyncIterable[MarketEvent],
        sink: DecisionSink | None = None,
    ) -> None:
        """Consume market events until the source ends."""
        async for event in source:
            decision = self.process(event)
            if decision is not None and sink is not None:
                await sink(decision)

    def _remember(self, event_id: str) -> None:
        if len(self._seen_order) == self._seen_order.maxlen:
            expired = self._seen_order[0]
            self._seen.discard(expired)
        self._seen_order.append(event_id)
        self._seen.add(event_id)
