from collections.abc import AsyncIterator
from decimal import Decimal

import pytest

from packages.autonomy import AutonomousControl, AutonomousMode
from packages.autonomy.decision import DecisionAction, MarketSnapshot
from packages.autonomy.loop import AutonomousSignalLoop, MarketEvent


def running_control() -> AutonomousControl:
    return (
        AutonomousControl()
        .with_mode(AutonomousMode.PAPER)
        .with_trading(True)
        .with_kill_switch(False)
        .start()
    )


def event(event_id: str = "btc-1", *, closed: bool = True, observed_at: float = 100.0) -> MarketEvent:
    return MarketEvent(
        event_id=event_id,
        snapshot=MarketSnapshot(
            symbol="BTCUSDT",
            price=Decimal("100000"),
            ema_fast=Decimal("101"),
            ema_slow=Decimal("100"),
            rsi=Decimal("55"),
            timestamp=100,
        ),
        closed=closed,
        observed_at=observed_at,
    )


def test_loop_evaluates_closed_fresh_event() -> None:
    loop = AutonomousSignalLoop(running_control, clock=lambda: 110.0)

    decision = loop.process(event())

    assert decision is not None
    assert decision.action is DecisionAction.BUY


def test_loop_fails_closed_when_control_is_disabled() -> None:
    loop = AutonomousSignalLoop(AutonomousControl, clock=lambda: 110.0)

    assert loop.process(event()) is None


def test_loop_ignores_unclosed_event() -> None:
    loop = AutonomousSignalLoop(running_control, clock=lambda: 110.0)

    assert loop.process(event(closed=False)) is None


def test_loop_ignores_stale_event() -> None:
    loop = AutonomousSignalLoop(running_control, max_event_age_seconds=5, clock=lambda: 110.0)

    assert loop.process(event(observed_at=100.0)) is None


def test_loop_ignores_future_event() -> None:
    loop = AutonomousSignalLoop(running_control, clock=lambda: 100.0)

    assert loop.process(event(observed_at=101.0)) is None


def test_loop_deduplicates_event_ids() -> None:
    loop = AutonomousSignalLoop(running_control, clock=lambda: 110.0)

    first = loop.process(event())
    second = loop.process(event())

    assert first is not None
    assert second is None


@pytest.mark.asyncio
async def test_loop_delivers_decisions_to_sink() -> None:
    loop = AutonomousSignalLoop(running_control, clock=lambda: 110.0)
    received = []

    async def source() -> AsyncIterator[MarketEvent]:
        yield event()

    async def sink(decision) -> None:
        received.append(decision)

    await loop.run(source(), sink)

    assert len(received) == 1
    assert received[0].action is DecisionAction.BUY


def test_event_requires_id() -> None:
    with pytest.raises(ValueError, match="event_id"):
        event("")


def test_loop_rejects_invalid_limits() -> None:
    with pytest.raises(ValueError):
        AutonomousSignalLoop(running_control, max_event_age_seconds=0)
    with pytest.raises(ValueError):
        AutonomousSignalLoop(running_control, dedupe_capacity=0)
