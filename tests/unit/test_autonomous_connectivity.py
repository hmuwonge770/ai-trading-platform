from packages.autonomy.connectivity import (
    AutonomousConnectivityMonitor,
    ConnectivityPolicy,
    ConnectivityState,
)


class Probe:
    def __init__(self, results: list[bool]) -> None:
        self.results = iter(results)

    def check(self) -> bool:
        return next(self.results)


def test_connectivity_starts_offline_and_recovers_after_successes() -> None:
    monitor = AutonomousConnectivityMonitor(probe=Probe([True, True]))

    first = monitor.check()
    second = monitor.check()

    assert first.state is ConnectivityState.OFFLINE
    assert first.reason == "recovery_pending"
    assert second.state is ConnectivityState.ONLINE


def test_single_failure_degrades() -> None:
    monitor = AutonomousConnectivityMonitor(
        probe=Probe([False]),
        initial_state=ConnectivityState.ONLINE,
    )

    report = monitor.check()

    assert report.state is ConnectivityState.DEGRADED
    assert report.consecutive_failures == 1


def test_repeated_failures_go_offline() -> None:
    monitor = AutonomousConnectivityMonitor(
        probe=Probe([False, False, False]),
        initial_state=ConnectivityState.ONLINE,
    )

    monitor.check()
    monitor.check()
    report = monitor.check()

    assert report.state is ConnectivityState.OFFLINE
    assert report.reason == "repeated_connectivity_failure"


def test_probe_exception_is_fail_closed() -> None:
    class FailingProbe:
        def check(self) -> bool:
            raise RuntimeError("transport unavailable")

    monitor = AutonomousConnectivityMonitor(
        probe=FailingProbe(),
        initial_state=ConnectivityState.ONLINE,
    )

    report = monitor.check()

    assert report.state is ConnectivityState.DEGRADED
    assert report.consecutive_failures == 1


def test_failure_resets_success_counter() -> None:
    monitor = AutonomousConnectivityMonitor(
        probe=Probe([True, False]),
        policy=ConnectivityPolicy(online_after=2),
        initial_state=ConnectivityState.DEGRADED,
    )

    monitor.check()
    report = monitor.check()

    assert report.consecutive_successes == 0
    assert report.consecutive_failures == 1
    assert report.state is ConnectivityState.DEGRADED


def test_invalid_policy_is_rejected() -> None:
    try:
        ConnectivityPolicy(degraded_after=2, offline_after=1)
    except ValueError as exc:
        assert "offline_after" in str(exc)
    else:
        raise AssertionError("invalid policy was accepted")


def test_monitor_does_not_retry_a_failed_probe() -> None:
    class CountingProbe:
        def __init__(self) -> None:
            self.calls = 0

        def check(self) -> bool:
            self.calls += 1
            return False

    probe = CountingProbe()
    monitor = AutonomousConnectivityMonitor(probe=probe)

    monitor.check()

    assert probe.calls == 1
