"""Deterministic, fail-closed disaster recovery controls for autonomous trading."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Protocol


class RecoveryStatus(str, Enum):
    READY = "ready"
    DEGRADED = "degraded"
    BLOCKED = "blocked"


class RecoveryAction(str, Enum):
    CONTINUE = "continue"
    RECOVER = "recover"
    HALT = "halt"


@dataclass(frozen=True, slots=True)
class RecoveryCheckpoint:
    checkpoint_id: str
    created_at: datetime
    state_version: str
    state_digest: str
    strategy_fingerprint: str

    def __post_init__(self) -> None:
        if not self.checkpoint_id or not self.state_version or not self.state_digest or not self.strategy_fingerprint:
            raise ValueError("checkpoint identity fields are required")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class RecoverySnapshot:
    snapshot_id: str
    created_at: datetime
    state_version: str
    state_digest: str
    strategy_fingerprint: str

    def __post_init__(self) -> None:
        if not self.snapshot_id or not self.state_version or not self.state_digest or not self.strategy_fingerprint:
            raise ValueError("snapshot identity fields are required")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class DisasterRecoveryPolicy:
    max_snapshot_age: timedelta = timedelta(minutes=5)
    require_strategy_match: bool = True

    def __post_init__(self) -> None:
        if self.max_snapshot_age <= timedelta(0):
            raise ValueError("max_snapshot_age must be positive")


@dataclass(frozen=True, slots=True)
class DisasterRecoveryReport:
    status: RecoveryStatus
    action: RecoveryAction
    healthy: bool
    reasons: tuple[str, ...]


class RecoveryStore(Protocol):
    def latest_checkpoint(self) -> RecoveryCheckpoint | None: ...
    def latest_snapshot(self) -> RecoverySnapshot | None: ...


class AutonomousDisasterRecovery:
    """Validate restart state before autonomous activity may continue."""

    def __init__(self, store: RecoveryStore, policy: DisasterRecoveryPolicy | None = None) -> None:
        self._store = store
        self._policy = policy or DisasterRecoveryPolicy()

    def assess(self, *, strategy_fingerprint: str, now: datetime | None = None) -> DisasterRecoveryReport:
        now = now or datetime.now(timezone.utc)
        reasons: list[str] = []
        if now.tzinfo is None:
            return DisasterRecoveryReport(RecoveryStatus.BLOCKED, RecoveryAction.HALT, False, ("now must be timezone-aware",))
        if not strategy_fingerprint:
            return DisasterRecoveryReport(RecoveryStatus.BLOCKED, RecoveryAction.HALT, False, ("strategy fingerprint is required",))

        checkpoint = self._store.latest_checkpoint()
        snapshot = self._store.latest_snapshot()
        if checkpoint is None or snapshot is None:
            return DisasterRecoveryReport(RecoveryStatus.BLOCKED, RecoveryAction.HALT, False, ("durable recovery state is unavailable",))
        if snapshot.created_at > now or checkpoint.created_at > now:
            return DisasterRecoveryReport(RecoveryStatus.BLOCKED, RecoveryAction.HALT, False, ("recovery state is from the future",))
        if now - snapshot.created_at > self._policy.max_snapshot_age:
            reasons.append("recovery snapshot is stale")
        if snapshot.state_version != checkpoint.state_version or snapshot.state_digest != checkpoint.state_digest:
            reasons.append("checkpoint and snapshot state do not match")
        if self._policy.require_strategy_match and snapshot.strategy_fingerprint != strategy_fingerprint:
            reasons.append("strategy fingerprint mismatch")
        if self._policy.require_strategy_match and checkpoint.strategy_fingerprint != strategy_fingerprint:
            reasons.append("checkpoint strategy fingerprint mismatch")

        if reasons:
            return DisasterRecoveryReport(RecoveryStatus.BLOCKED, RecoveryAction.HALT, False, tuple(reasons))
        return DisasterRecoveryReport(RecoveryStatus.READY, RecoveryAction.CONTINUE, True, ())
