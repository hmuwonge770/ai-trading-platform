from datetime import datetime, timedelta, timezone

import pytest

from packages.autonomy.disaster_recovery import (
    AutonomousDisasterRecovery,
    DisasterRecoveryPolicy,
    RecoveryCheckpoint,
    RecoverySnapshot,
    RecoveryStatus,
    RecoveryAction,
)


class Store:
    def __init__(self, checkpoint=None, snapshot=None):
        self.checkpoint = checkpoint
        self.snapshot = snapshot

    def latest_checkpoint(self):
        return self.checkpoint

    def latest_snapshot(self):
        return self.snapshot


def state(now):
    return (
        RecoveryCheckpoint("cp-1", now - timedelta(seconds=10), "v1", "digest-1", "strategy-1"),
        RecoverySnapshot("snap-1", now - timedelta(seconds=5), "v1", "digest-1", "strategy-1"),
    )


def test_matching_state_is_ready():
    now = datetime.now(timezone.utc)
    checkpoint, snapshot = state(now)
    report = AutonomousDisasterRecovery(Store(checkpoint, snapshot)).assess(strategy_fingerprint="strategy-1", now=now)
    assert report.status is RecoveryStatus.READY
    assert report.action is RecoveryAction.CONTINUE
    assert report.healthy


def test_missing_durable_state_halts():
    report = AutonomousDisasterRecovery(Store()).assess(strategy_fingerprint="strategy-1", now=datetime.now(timezone.utc))
    assert report.status is RecoveryStatus.BLOCKED
    assert report.action is RecoveryAction.HALT


def test_stale_snapshot_halts():
    now = datetime.now(timezone.utc)
    checkpoint = RecoveryCheckpoint("cp", now - timedelta(minutes=10), "v1", "d", "s")
    snapshot = RecoverySnapshot("snap", now - timedelta(minutes=10), "v1", "d", "s")
    report = AutonomousDisasterRecovery(Store(checkpoint, snapshot)).assess(strategy_fingerprint="s", now=now)
    assert report.action is RecoveryAction.HALT
    assert "stale" in report.reasons[0]


def test_state_mismatch_halts():
    now = datetime.now(timezone.utc)
    checkpoint = RecoveryCheckpoint("cp", now, "v1", "d1", "s")
    snapshot = RecoverySnapshot("snap", now, "v2", "d2", "s")
    report = AutonomousDisasterRecovery(Store(checkpoint, snapshot)).assess(strategy_fingerprint="s", now=now)
    assert report.status is RecoveryStatus.BLOCKED
    assert any("match" in reason for reason in report.reasons)


def test_strategy_mismatch_halts():
    now = datetime.now(timezone.utc)
    checkpoint, snapshot = state(now)
    report = AutonomousDisasterRecovery(Store(checkpoint, snapshot)).assess(strategy_fingerprint="other", now=now)
    assert report.action is RecoveryAction.HALT
    assert any("fingerprint" in reason for reason in report.reasons)


def test_invalid_checkpoint_timestamp_is_rejected():
    with pytest.raises(ValueError):
        RecoveryCheckpoint("cp", datetime.now(), "v1", "d", "s")
