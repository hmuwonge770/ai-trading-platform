from datetime import datetime, timezone

from packages.reliability.faults import FailurePlan
from packages.reliability.soak import DeterministicSoakRunner, SoakConfig


def test_72_hour_virtual_soak_recovers_injected_failures() -> None:
    plan = FailurePlan(fail_on=frozenset({97, 193, 289, 385}))
    report = DeterministicSoakRunner(SoakConfig(failure_plan=plan)).run()

    assert report.duration.total_seconds() == 72 * 60 * 60
    assert report.ticks == 432
    assert report.successful_ticks == 428
    assert report.injected_failures == 4
    assert report.recovered_failures == 4
    assert report.duplicate_events == 0
    assert report.invariant_violations == 0
    assert report.final_balance == 432
    assert report.healthy


def test_soak_requires_timezone_aware_start() -> None:
    runner = DeterministicSoakRunner()

    try:
        runner.run(datetime(2026, 1, 1))
    except ValueError as exc:
        assert "timezone-aware" in str(exc)
    else:
        raise AssertionError("naive start must be rejected")


def test_soak_can_run_from_explicit_utc_start() -> None:
    report = DeterministicSoakRunner().run(datetime(2026, 6, 1, tzinfo=timezone.utc))

    assert report.healthy
    assert report.duration.total_seconds() == 72 * 60 * 60
