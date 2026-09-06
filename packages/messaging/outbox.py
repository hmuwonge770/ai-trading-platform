from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Protocol
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.database.outbox import OutboxEvent, OutboxStatus


class OutboxPublisher(Protocol):
    def publish(self, event: OutboxEvent) -> None:
        """Publish an event to the durable message broker."""


class OutboxRepository:
    def __init__(self, db: Session):
        self.db = db

    def enqueue(
        self,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: dict,
    ) -> OutboxEvent:
        event = OutboxEvent(
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
        )
        self.db.add(event)
        self.db.flush()
        return event

    def claim_one(self, now: datetime | None = None) -> OutboxEvent | None:
        now = now or datetime.now(timezone.utc)
        event = self.db.scalar(
            select(OutboxEvent)
            .where(
                OutboxEvent.status == OutboxStatus.PENDING,
                OutboxEvent.available_at <= now,
            )
            .order_by(OutboxEvent.created_at, OutboxEvent.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if event is None:
            return None
        event.attempts += 1
        self.db.flush()
        return event

    def mark_published(self, event: OutboxEvent, now: datetime | None = None) -> None:
        event.status = OutboxStatus.PUBLISHED
        event.published_at = now or datetime.now(timezone.utc)
        event.last_error = None
        self.db.flush()

    def mark_failed(
        self,
        event: OutboxEvent,
        error: str,
        retry_after_seconds: int = 5,
        now: datetime | None = None,
    ) -> None:
        now = now or datetime.now(timezone.utc)
        event.status = OutboxStatus.PENDING
        event.last_error = error[:4000]
        event.available_at = now + timedelta(seconds=retry_after_seconds)
        self.db.flush()


class OutboxDispatcher:
    """At-least-once dispatcher; consumers must deduplicate by event id."""

    def __init__(self, repository: OutboxRepository, publisher: OutboxPublisher):
        self.repository = repository
        self.publisher = publisher

    def dispatch_one(self, now: datetime | None = None) -> uuid.UUID | None:
        event = self.repository.claim_one(now=now)
        if event is None:
            return None
        try:
            self.publisher.publish(event)
        except Exception as exc:
            self.repository.mark_failed(event, str(exc), now=now)
            self.repository.db.commit()
            return event.id
        self.repository.mark_published(event, now=now)
        self.repository.db.commit()
        return event.id
