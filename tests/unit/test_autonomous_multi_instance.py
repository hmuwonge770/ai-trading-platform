from __future__ import annotations

import pytest

from packages.autonomy.multi_instance import (
    AutonomousInstanceCoordinator,
    CoordinationStatus,
    InMemoryCoordinationStore,
)


def test_only_one_instance_can_hold_a_key() -> None:
    store = InMemoryCoordinationStore()
    first = AutonomousInstanceCoordinator(store, ttl_seconds=10).acquire(key="BTCUSDT", owner_id="a", now=100)
    second = AutonomousInstanceCoordinator(store, ttl_seconds=10).acquire(key="BTCUSDT", owner_id="b", now=101)
    assert first.status is CoordinationStatus.ACQUIRED
    assert second.status is CoordinationStatus.HELD
    assert first.lease is not None
    assert first.lease.fencing_token == 1


def test_expiry_allows_new_owner_with_new_fencing_token() -> None:
    store = InMemoryCoordinationStore()
    coordinator = AutonomousInstanceCoordinator(store, ttl_seconds=10)
    first = coordinator.acquire(key="strategy", owner_id="a", now=100)
    second = coordinator.acquire(key="strategy", owner_id="b", now=110)
    assert first.lease is not None and second.lease is not None
    assert second.status is CoordinationStatus.ACQUIRED
    assert second.lease.fencing_token == first.lease.fencing_token + 1
    assert not coordinator.can_act(first.lease, now=110)
    assert coordinator.can_act(second.lease, now=110)


def test_release_requires_current_owner_lease() -> None:
    store = InMemoryCoordinationStore()
    coordinator = AutonomousInstanceCoordinator(store)
    first = coordinator.acquire(key="strategy", owner_id="a", now=100)
    assert first.lease is not None
    assert coordinator.release(first.lease, now=101).status is CoordinationStatus.RELEASED
    assert coordinator.release(first.lease, now=102).status is CoordinationStatus.CONFLICT


def test_coordination_failure_fails_closed() -> None:
    class BrokenStore:
        def acquire(self, key: str, owner_id: str, now: int, ttl_seconds: int):
            raise OSError("down")

        def release(self, lease, now: int):
            raise OSError("down")

        def valid(self, lease, now: int):
            raise OSError("down")

    coordinator = AutonomousInstanceCoordinator(BrokenStore())
    report = coordinator.acquire(key="strategy", owner_id="a", now=100)
    assert report.status is CoordinationStatus.UNAVAILABLE
    assert coordinator.can_act(object(), now=100) is False


def test_invalid_lease_is_rejected() -> None:
    with pytest.raises(ValueError):
        from packages.autonomy.multi_instance import CoordinationLease

        CoordinationLease("", "a", 1, 1, 2)
