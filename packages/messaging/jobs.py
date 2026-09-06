from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from packages.messaging.messages import JobMessage


@dataclass(frozen=True, slots=True)
class JobSpec:
    """Validated application-level description of one asynchronous research job."""

    job_type: str
    payload: dict
    session_id: UUID | None = None
    experiment_id: UUID | None = None
    max_attempts: int = 3

    def __post_init__(self) -> None:
        if not self.job_type.strip():
            raise ValueError("job_type must not be empty")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least one")

    def message(self, job_id: UUID | None = None) -> JobMessage:
        return JobMessage(
            job_id=job_id or uuid4(),
            job_type=self.job_type,
            payload=self.payload,
            session_id=self.session_id,
            experiment_id=self.experiment_id,
            attempt=1,
            max_attempts=self.max_attempts,
            created_at=datetime.now(timezone.utc),
        )
