import pytest

from packages.autonomy.connectivity import ConnectivityPolicy, ConnectivityReport, ConnectivityState


def test_connectivity_policy_is_immutable() -> None:
    policy = ConnectivityPolicy()
    with pytest.raises((AttributeError, TypeError)):
        policy.offline_after = 9  # type: ignore[misc]


def test_connectivity_report_is_immutable() -> None:
    report = ConnectivityReport(
        state=ConnectivityState.ONLINE,
        previous_state=ConnectivityState.DEGRADED,
        consecutive_failures=0,
        consecutive_successes=2,
        reason="connectivity_recovered",
    )
    with pytest.raises((AttributeError, TypeError)):
        report.reason = "changed"  # type: ignore[misc]
