from __future__ import annotations

import json

import pytest

from packages.autonomy.persistent_state import (
    AutonomousPersistentState,
    AutonomousStateSnapshot,
    InMemoryPersistentStateStore,
    JsonFilePersistentStateStore,
    PersistentStatePolicy,
    PersistentStateStatus,
)


def snapshot(**overrides: object) -> AutonomousStateSnapshot:
    values: dict[str, object] = {
        "schema_version": 1,
        "revision": 1,
        "captured_at": 100,
        "lifecycle_state": "running",
        "trading_mode": "paper",
        "kill_switch_enabled": False,
        "circuit_breaker_open": False,
        "strategy_fingerprint": "sha256:abc",
        "expected_position_symbols": ("BTCUSDT",),
        "pending_order_ids": ("client-1",),
    }
    values.update(overrides)
    return AutonomousStateSnapshot(**values)  # type: ignore[arg-type]


def test_round_trip_snapshot_is_immutable_and_secret_free() -> None:
    state = snapshot()
    payload = state.to_dict()
    assert AutonomousStateSnapshot.from_dict(payload) == state
    assert "api_key" not in json.dumps(payload)
    with pytest.raises((AttributeError, TypeError)):
        state.revision = 2  # type: ignore[misc]


def test_memory_store_rejects_non_monotonic_revisions() -> None:
    store = InMemoryPersistentStateStore()
    store.save(snapshot())
    with pytest.raises(ValueError, match="revision"):
        store.save(snapshot(revision=1))


def test_restore_empty_is_not_safe() -> None:
    manager = AutonomousPersistentState(InMemoryPersistentStateStore())
    report = manager.restore(now=100)
    assert report.status is PersistentStateStatus.EMPTY
    assert not report.safe_to_resume


def test_restore_fresh_state_is_safe_only_when_controls_are_clear() -> None:
    store = InMemoryPersistentStateStore()
    manager = AutonomousPersistentState(store)
    manager.persist(snapshot())
    report = manager.restore(now=120)
    assert report.status is PersistentStateStatus.RESTORED
    assert report.safe_to_resume


def test_restore_with_kill_switch_or_breaker_never_resumes() -> None:
    for field in ("kill_switch_enabled", "circuit_breaker_open"):
        store = InMemoryPersistentStateStore()
        manager = AutonomousPersistentState(store)
        manager.persist(snapshot(**{field: True}))
        report = manager.restore(now=120)
        assert report.status is PersistentStateStatus.RESTORED
        assert not report.safe_to_resume
        assert report.reasons == ("safety_control_active",)


def test_restore_stale_or_future_state_fails_closed() -> None:
    store = InMemoryPersistentStateStore()
    manager = AutonomousPersistentState(store, policy=PersistentStatePolicy(max_age_seconds=30))
    manager.persist(snapshot())
    assert manager.restore(now=131).status is PersistentStateStatus.STALE
    assert not manager.restore(now=131).safe_to_resume

    future_store = InMemoryPersistentStateStore()
    future_manager = AutonomousPersistentState(future_store)
    future_manager.persist(snapshot(captured_at=200))
    report = future_manager.restore(now=100)
    assert report.status is PersistentStateStatus.STALE
    assert not report.safe_to_resume


def test_corrupt_file_fails_closed(tmp_path) -> None:
    path = tmp_path / "state.json"
    path.write_text("not-json", encoding="utf-8")
    manager = AutonomousPersistentState(JsonFilePersistentStateStore(path))
    report = manager.restore(now=100)
    assert report.status is PersistentStateStatus.CORRUPT
    assert not report.safe_to_resume


def test_file_store_round_trip_and_monotonic_revision(tmp_path) -> None:
    path = tmp_path / "runtime" / "state.json"
    store = JsonFilePersistentStateStore(path)
    store.save(snapshot())
    assert store.load() == snapshot()
    with pytest.raises(ValueError, match="revision"):
        store.save(snapshot(revision=1))
    store.save(snapshot(revision=2, captured_at=110))
    assert store.load() == snapshot(revision=2, captured_at=110)
