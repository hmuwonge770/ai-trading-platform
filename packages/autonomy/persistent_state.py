"""Restart-safe, secret-free persistence primitives for autonomous state."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol


class PersistentStateStatus(StrEnum):
    RESTORED = "restored"
    EMPTY = "empty"
    STALE = "stale"
    CORRUPT = "corrupt"
    CONFLICT = "conflict"


@dataclass(frozen=True, slots=True)
class AutonomousStateSnapshot:
    """Durable state required to safely resume after a process restart.

    The snapshot is deliberately limited to operational metadata. Secrets,
    credentials, market data, orders, and arbitrary AI instructions are never
    persisted by this component.
    """

    schema_version: int
    revision: int
    captured_at: int
    lifecycle_state: str
    trading_mode: str
    kill_switch_enabled: bool
    circuit_breaker_open: bool
    strategy_fingerprint: str | None = None
    expected_position_symbols: tuple[str, ...] = ()
    pending_order_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.schema_version <= 0:
            raise ValueError("schema_version must be positive")
        if self.revision <= 0:
            raise ValueError("revision must be positive")
        if self.captured_at <= 0:
            raise ValueError("captured_at must be positive")
        if not self.lifecycle_state.strip():
            raise ValueError("lifecycle_state must not be empty")
        if not self.trading_mode.strip():
            raise ValueError("trading_mode must not be empty")
        if self.strategy_fingerprint is not None and not self.strategy_fingerprint.strip():
            raise ValueError("strategy_fingerprint must not be blank")
        if any(not item.strip() for item in self.expected_position_symbols):
            raise ValueError("expected_position_symbols must not contain blanks")
        if any(not item.strip() for item in self.pending_order_ids):
            raise ValueError("pending_order_ids must not contain blanks")
        if len(set(self.expected_position_symbols)) != len(self.expected_position_symbols):
            raise ValueError("expected_position_symbols must be unique")
        if len(set(self.pending_order_ids)) != len(self.pending_order_ids):
            raise ValueError("pending_order_ids must be unique")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "revision": self.revision,
            "captured_at": self.captured_at,
            "lifecycle_state": self.lifecycle_state,
            "trading_mode": self.trading_mode,
            "kill_switch_enabled": self.kill_switch_enabled,
            "circuit_breaker_open": self.circuit_breaker_open,
            "strategy_fingerprint": self.strategy_fingerprint,
            "expected_position_symbols": list(self.expected_position_symbols),
            "pending_order_ids": list(self.pending_order_ids),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "AutonomousStateSnapshot":
        return cls(
            schema_version=_positive_int(payload, "schema_version"),
            revision=_positive_int(payload, "revision"),
            captured_at=_positive_int(payload, "captured_at"),
            lifecycle_state=_string(payload, "lifecycle_state"),
            trading_mode=_string(payload, "trading_mode"),
            kill_switch_enabled=_bool(payload, "kill_switch_enabled"),
            circuit_breaker_open=_bool(payload, "circuit_breaker_open"),
            strategy_fingerprint=_optional_string(payload, "strategy_fingerprint"),
            expected_position_symbols=_string_tuple(payload, "expected_position_symbols"),
            pending_order_ids=_string_tuple(payload, "pending_order_ids"),
        )


class PersistentStateStore(Protocol):
    def save(self, snapshot: AutonomousStateSnapshot) -> None: ...

    def load(self) -> AutonomousStateSnapshot | None: ...


class InMemoryPersistentStateStore:
    """Reference store used by tests and embedding applications."""

    def __init__(self) -> None:
        self._snapshot: AutonomousStateSnapshot | None = None

    def save(self, snapshot: AutonomousStateSnapshot) -> None:
        if self._snapshot is not None and snapshot.revision <= self._snapshot.revision:
            raise ValueError("state revision must increase monotonically")
        self._snapshot = snapshot

    def load(self) -> AutonomousStateSnapshot | None:
        return self._snapshot


class JsonFilePersistentStateStore:
    """Atomic JSON-file store for secret-free autonomous state.

    Writes use a temporary file in the same directory followed by ``os.replace``
    so a process crash cannot intentionally overwrite the target with a partial
    JSON document. File permissions are restricted to the current user.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        if not self.path.name:
            raise ValueError("path must identify a file")

    def save(self, snapshot: AutonomousStateSnapshot) -> None:
        current = self.load()
        if current is not None and snapshot.revision <= current.revision:
            raise ValueError("state revision must increase monotonically")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=f".{self.path.name}.", dir=self.path.parent)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(snapshot.to_dict(), handle, sort_keys=True, separators=(",", ":"))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def load(self) -> AutonomousStateSnapshot | None:
        if not self.path.exists():
            return None
        with self.path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            raise ValueError("persistent state root must be an object")
        return AutonomousStateSnapshot.from_dict(payload)


@dataclass(frozen=True, slots=True)
class PersistentStatePolicy:
    schema_version: int = 1
    max_age_seconds: int = 60

    def __post_init__(self) -> None:
        if self.schema_version <= 0:
            raise ValueError("schema_version must be positive")
        if self.max_age_seconds <= 0:
            raise ValueError("max_age_seconds must be positive")


@dataclass(frozen=True, slots=True)
class PersistentStateReport:
    status: PersistentStateStatus
    safe_to_resume: bool
    reasons: tuple[str, ...]
    snapshot: AutonomousStateSnapshot | None = None


class AutonomousPersistentState:
    """Persist and validate restart state; never grant trading authority."""

    def __init__(self, store: PersistentStateStore, *, policy: PersistentStatePolicy | None = None) -> None:
        self.store = store
        self.policy = policy or PersistentStatePolicy()

    def persist(self, snapshot: AutonomousStateSnapshot) -> None:
        if snapshot.schema_version != self.policy.schema_version:
            raise ValueError("unsupported state schema version")
        self.store.save(snapshot)

    def restore(self, *, now: int) -> PersistentStateReport:
        try:
            snapshot = self.store.load()
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return PersistentStateReport(PersistentStateStatus.CORRUPT, False, ("state_unavailable_or_corrupt",))
        if snapshot is None:
            return PersistentStateReport(PersistentStateStatus.EMPTY, False, ("no_persisted_state",))
        if snapshot.schema_version != self.policy.schema_version:
            return PersistentStateReport(PersistentStateStatus.CORRUPT, False, ("unsupported_schema_version",), snapshot)
        if now <= 0:
            return PersistentStateReport(PersistentStateStatus.CORRUPT, False, ("invalid_restore_time",), snapshot)
        age = now - snapshot.captured_at
        if age < 0 or age > self.policy.max_age_seconds:
            return PersistentStateReport(PersistentStateStatus.STALE, False, ("state_stale",), snapshot)
        if snapshot.kill_switch_enabled or snapshot.circuit_breaker_open:
            return PersistentStateReport(PersistentStateStatus.RESTORED, False, ("safety_control_active",), snapshot)
        return PersistentStateReport(PersistentStateStatus.RESTORED, True, (), snapshot)


def _positive_int(payload: dict[str, object], key: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{key} must be a positive integer")
    return value


def _string(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _optional_string(payload: dict[str, object], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string or null")
    return value


def _bool(payload: dict[str, object], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be boolean")
    return value


def _string_tuple(payload: dict[str, object], key: str) -> tuple[str, ...]:
    value = payload.get(key)
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{key} must be a list of non-empty strings")
    return tuple(value)
