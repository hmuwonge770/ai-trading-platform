from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class JobMessage:
    job_id: uuid.UUID
    job_type: str
    payload: dict
    session_id: uuid.UUID | None = None
    experiment_id: uuid.UUID | None = None
    attempt: int = 1
    max_attempts: int = 3
    created_at: datetime | None = None

    def to_bytes(self) -> bytes:
        value = asdict(self)
        value["job_id"] = str(self.job_id)
        value["session_id"] = str(self.session_id) if self.session_id else None
        value["experiment_id"] = str(self.experiment_id) if self.experiment_id else None
        value["created_at"] = (self.created_at or datetime.now(timezone.utc)).isoformat()
        return json.dumps(value, separators=(",", ":"), sort_keys=True).encode()
