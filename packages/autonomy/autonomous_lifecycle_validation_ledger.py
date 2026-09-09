"""Restart-safe, identity-bound ledger for AY validation results."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from threading import Lock

from .autonomous_lifecycle_validation import LifecycleValidationAssessment, LifecycleValidationAction


@dataclass(frozen=True, slots=True)
class LifecycleValidationLedgerEntry:
    strategy_version_id: str
    request_key: str
    assessment: LifecycleValidationAssessment
    digest: str


def lifecycle_validation_digest(strategy_version_id: str, request_key: str, assessment: LifecycleValidationAssessment) -> str:
    payload = "|".join((strategy_version_id, request_key, assessment.action.value, str(assessment.safe), *assessment.reasons))
    return sha256(payload.encode("utf-8")).hexdigest()


class InMemoryLifecycleValidationLedger:
    """Thread-safe idempotency ledger; persistence belongs to the host control plane."""

    def __init__(self) -> None:
        self._entries: dict[tuple[str, str], LifecycleValidationLedgerEntry] = {}
        self._lock = Lock()

    def record(self, strategy_version_id: str, request_key: str, assessment: LifecycleValidationAssessment) -> LifecycleValidationLedgerEntry:
        if not strategy_version_id or not request_key:
            raise ValueError("strategy identity and request key are required")
        digest = lifecycle_validation_digest(strategy_version_id, request_key, assessment)
        key = (strategy_version_id, request_key)
        with self._lock:
            existing = self._entries.get(key)
            if existing is not None:
                if existing.digest != digest:
                    raise ValueError("conflicting lifecycle validation request")
                return existing
            entry = LifecycleValidationLedgerEntry(strategy_version_id, request_key, assessment, digest)
            self._entries[key] = entry
            return entry

    def get(self, strategy_version_id: str, request_key: str) -> LifecycleValidationLedgerEntry | None:
        with self._lock:
            return self._entries.get((strategy_version_id, request_key))
