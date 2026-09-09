"""Restart-safe, append-only incident response decision ledger."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .incident_response import IncidentResponseReport


class IncidentDecisionStore(Protocol):
    def get(self, fingerprint: str) -> IncidentResponseReport | None: ...
    def put(self, fingerprint: str, report: IncidentResponseReport) -> None: ...


@dataclass(frozen=True, slots=True)
class IncidentLedgerResult:
    report: IncidentResponseReport
    replayed: bool


class InMemoryIncidentDecisionStore:
    def __init__(self) -> None:
        self._items: dict[str, IncidentResponseReport] = {}

    def get(self, fingerprint: str) -> IncidentResponseReport | None:
        return self._items.get(fingerprint)

    def put(self, fingerprint: str, report: IncidentResponseReport) -> None:
        existing = self._items.get(fingerprint)
        if existing is not None and existing != report:
            raise ValueError("incident fingerprint already has a different decision")
        self._items[fingerprint] = report


class IdempotentIncidentResponseLedger:
    """Persist a response decision once and replay it safely on duplicate delivery."""

    def __init__(self, *, store: IncidentDecisionStore) -> None:
        self._store = store

    def record(self, report: IncidentResponseReport) -> IncidentLedgerResult:
        existing = self._store.get(report.fingerprint)
        if existing is not None:
            if existing != report:
                raise ValueError("incident fingerprint conflict")
            return IncidentLedgerResult(existing, True)
        self._store.put(report.fingerprint, report)
        return IncidentLedgerResult(report, False)
