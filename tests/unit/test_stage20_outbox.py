from datetime import datetime, timezone
from types import SimpleNamespace
import uuid

from packages.database.outbox import OutboxStatus
from packages.messaging.outbox import OutboxDispatcher


class FakeRepository:
    def __init__(self, event):
        self.event = event
        self.db = SimpleNamespace(commit=lambda: None)
        self.published = False
        self.failed = False

    def claim_one(self, now=None):
        if self.event is None:
            return None
        event, self.event = self.event, None
        event.attempts += 1
        return event

    def mark_published(self, event, now=None):
        self.published = True
        event.status = OutboxStatus.PUBLISHED

    def mark_failed(self, event, error, retry_after_seconds=5, now=None):
        self.failed = True
        event.status = OutboxStatus.PENDING
        event.last_error = error


class FakePublisher:
    def __init__(self, error=None):
        self.error = error
        self.events = []

    def publish(self, event):
        if self.error:
            raise RuntimeError(self.error)
        self.events.append(event.id)


def make_event():
    return SimpleNamespace(
        id=uuid.uuid4(),
        event_type="execution.accepted",
        aggregate_type="order",
        aggregate_id="order-1",
        payload={"symbol": "BTCUSDT"},
        status=OutboxStatus.PENDING,
        attempts=0,
        last_error=None,
    )


def test_dispatch_publishes_and_marks_event():
    event = make_event()
    repository = FakeRepository(event)
    publisher = FakePublisher()

    result = OutboxDispatcher(repository, publisher).dispatch_one()

    assert result == event.id
    assert publisher.events == [event.id]
    assert repository.published
    assert event.status == OutboxStatus.PUBLISHED
    assert event.attempts == 1


def test_dispatch_failure_keeps_event_pending_for_retry():
    event = make_event()
    repository = FakeRepository(event)
    publisher = FakePublisher("broker unavailable")

    result = OutboxDispatcher(repository, publisher).dispatch_one()

    assert result == event.id
    assert repository.failed
    assert event.status == OutboxStatus.PENDING
    assert event.last_error == "broker unavailable"


def test_empty_outbox_does_nothing():
    repository = FakeRepository(None)
    publisher = FakePublisher()

    assert OutboxDispatcher(repository, publisher).dispatch_one() is None
    assert publisher.events == []


def test_dispatch_accepts_explicit_timestamp():
    event = make_event()
    repository = FakeRepository(event)
    publisher = FakePublisher()
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)

    assert OutboxDispatcher(repository, publisher).dispatch_one(now=now) == event.id
