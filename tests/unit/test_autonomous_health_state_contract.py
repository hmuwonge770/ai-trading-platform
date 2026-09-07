import pytest

from packages.autonomy.health_state import HealthObservation, HealthStateReport


def test_health_observation_is_immutable() -> None:
    observation = HealthObservation(True, True, True, True, False, 100)
    with pytest.raises((AttributeError, TypeError)):
        observation.observed_at = 101  # type: ignore[misc]


def test_health_report_is_immutable() -> None:
    report = HealthStateReport(
        state="healthy",
        previous_state="degraded",
        consecutive_unhealthy=0,
        consecutive_healthy=2,
        reason="health_recovered",
        observed_at=100,
    )
    with pytest.raises((AttributeError, TypeError)):
        report.reason = "changed"  # type: ignore[misc]
