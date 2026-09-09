"""Restart-safe, idempotent ledger for expansion recommendations."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from threading import Lock
from uuid import UUID

from .controlled_expansion import ExpansionReport


@dataclass(frozen=True, slots=True)
class ExpansionLedgerEntry:
    strategy_version_id: UUID
    request_key: str
    report_digest: str
    report: ExpansionReport


def expansion_report_digest(report: ExpansionReport) -> str:
    payload = "|".join((
        str(report.strategy_version_id), report.action.value,
        str(report.safe), str(report.current_cohort_percent),
        str(report.requested_cohort_percent), str(report.approved_delta_percent),
        *report.reasons,
    ))
    return sha256(payload.encode("utf-8")).hexdigest()


class InMemoryExpansionLedger:
    """Thread-safe idempotency store; it does not execute or mutate runtime state."""

    def __init__(self) -> None:
        self._entries: dict[tuple[UUID, str], ExpansionLedgerEntry] = {}
        self._lock = Lock()

    def record(self, *, strategy_version_id: UUID, request_key: str, report: ExpansionReport) -> ExpansionLedgerEntry:
        if not request_key:
            raise ValueError("request_key is required")
        if report.strategy_version_id != strategy_version_id:
            raise ValueError("strategy identity mismatch")
        key = (strategy_version_id, request_key)
        entry = ExpansionLedgerEntry(strategy_version_id, request_key, expansion_report_digest(report), report)
        with self._lock:
            existing = self._entries.get(key)
            if existing is not None:
                if existing.report_digest != entry.report_digest:
                    raise ValueError("request key already maps to a different expansion decision")
                return existing
            self._entries[key] = entry
            return entry

    def get(self, *, strategy_version_id: UUID, request_key: str) -> ExpansionLedgerEntry | None:
        with self._lock:
            return self._entries.get((strategy_version_id, request_key))
