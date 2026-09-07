"""Fail-closed coordination primitives for multiple autonomous instances."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from threading import Lock
from typing import Protocol


class CoordinationStatus(StrEnum):
    ACQUIRED = "acquired"
    HELD = "held"
    RELEASED = "released"
    EXPIRED = "expired"
    CONFLICT = "conflict"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class CoordinationLease:
    key: str
    owner_id: str
    fencing_token: int
    acquired_at: int
    expires_at: int

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.owner_id.strip():
            raise ValueError("key and owner_id must not be empty")
        if self.fencing_token <= 0 or self.acquired_at <= 0 or self.expires_at <= self.acquired_at:
            raise ValueError("invalid lease values")


@dataclass(frozen=True, slots=True)
class CoordinationReport:
    status: CoordinationStatus
    lease: CoordinationLease | None = None
    reason: str = ""


class CoordinationStore(Protocol):
    def acquire(self, key: str, owner_id: str, now: int, ttl_seconds: int) -> CoordinationLease | None: ...
    def release(self, lease: CoordinationLease, now: int) -> bool: ...
    def valid(self, lease: CoordinationLease, now: int) -> bool: ...


class InMemoryCoordinationStore:
    """Reference atomic coordinator; production deployments inject a shared store."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._leases: dict[str, CoordinationLease] = {}
        self._tokens: dict[str, int] = {}

    def acquire(self, key: str, owner_id: str, now: int, ttl_seconds: int) -> CoordinationLease | None:
        if not key.strip() or not owner_id.strip() or now <= 0 or ttl_seconds <= 0:
            raise ValueError("invalid coordination request")
        with self._lock:
            current = self._leases.get(key)
            if current is not None and current.expires_at > now:
                return None
            token = self._tokens.get(key, 0) + 1
            lease = CoordinationLease(key, owner_id, token, now, now + ttl_seconds)
            self._tokens[key] = token
            self._leases[key] = lease
            return lease

    def release(self, lease: CoordinationLease, now: int) -> bool:
        with self._lock:
            current = self._leases.get(lease.key)
            if current != lease or now <= 0:
                return False
            del self._leases[lease.key]
            return True

    def valid(self, lease: CoordinationLease, now: int) -> bool:
        with self._lock:
            return self._leases.get(lease.key) == lease and lease.expires_at > now


class AutonomousInstanceCoordinator:
    """Coordinates ownership without granting order or authorization authority."""

    def __init__(self, store: CoordinationStore, *, ttl_seconds: int = 15) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self.store = store
        self.ttl_seconds = ttl_seconds

    def acquire(self, *, key: str, owner_id: str, now: int) -> CoordinationReport:
        try:
            lease = self.store.acquire(key, owner_id, now, self.ttl_seconds)
        except (OSError, ValueError, RuntimeError):
            return CoordinationReport(CoordinationStatus.UNAVAILABLE, reason="coordination_unavailable")
        if lease is None:
            return CoordinationReport(CoordinationStatus.HELD, reason="lease_held_by_other_instance")
        return CoordinationReport(CoordinationStatus.ACQUIRED, lease=lease)

    def release(self, lease: CoordinationLease, *, now: int) -> CoordinationReport:
        try:
            released = self.store.release(lease, now)
        except (OSError, ValueError, RuntimeError):
            return CoordinationReport(CoordinationStatus.UNAVAILABLE, lease=lease, reason="coordination_unavailable")
        if released:
            return CoordinationReport(CoordinationStatus.RELEASED, lease=lease)
        return CoordinationReport(CoordinationStatus.CONFLICT, lease=lease, reason="lease_not_owned")

    def can_act(self, lease: CoordinationLease, *, now: int) -> bool:
        try:
            return self.store.valid(lease, now)
        except (OSError, ValueError, RuntimeError):
            return False
