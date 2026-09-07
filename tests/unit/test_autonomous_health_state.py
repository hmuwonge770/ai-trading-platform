from packages.autonomy.health_state import (
    AutonomousHealthState,
    AutonomousHealthStateMachine,
    HealthObservation,
    HealthStatePolicy,
)


def healthy(at: int) -> HealthObservation:
    return HealthObservation(True, True, True, True, False, at)


def unsafe(at: int) -> HealthObservation:
    return HealthObservation(True, True, False, True, False, at)


def test_machine_starts_halted_and_requires_recovery_observations() -> None:
    machine = AutonomousHealthStateMachine()
    first = machine.observe(healthy(1))
    second = machine.observe(healthy(2))

    assert first.state is AutonomousHealthState.HALTED
    assert first.reason == "recovery_pending"
    assert second.state is AutonomousHealthState.HEALTHY


def test_single_unsafe_observation_degrades() -> None:
    machine = AutonomousHealthStateMachine(initial_state=AutonomousHealthState.HEALTHY)

    report = machine.observe(unsafe(10))

    assert report.state is AutonomousHealthState.DEGRADED
    assert report.reason == "unsafe_health"
    assert report.consecutive_unhealthy == 1


def test_repeated_unsafe_observations_halt() -> None:
    machine = AutonomousHealthStateMachine(initial_state=AutonomousHealthState.HEALTHY)

    machine.observe(unsafe(10))
    report = machine.observe(unsafe(11))

    assert report.state is AutonomousHealthState.HALTED
    assert report.reason == "repeated_unsafe_health"


def test_kill_switch_halts_immediately() -> None:
    machine = AutonomousHealthStateMachine(initial_state=AutonomousHealthState.HEALTHY)
    observation = HealthObservation(True, True, True, True, True, 20)

    report = machine.observe(observation)

    assert report.state is AutonomousHealthState.HALTED
    assert report.reason == "kill_switch_enabled"


def test_recovery_requires_consecutive_healthy_observations() -> None:
    machine = AutonomousHealthStateMachine(
        policy=HealthStatePolicy(healthy_after=3),
        initial_state=AutonomousHealthState.DEGRADED,
    )

    first = machine.observe(healthy(30))
    second = machine.observe(healthy(31))
    third = machine.observe(healthy(32))

    assert first.state is AutonomousHealthState.DEGRADED
    assert second.state is AutonomousHealthState.DEGRADED
    assert third.state is AutonomousHealthState.HEALTHY


def test_unhealthy_observation_resets_recovery_counter() -> None:
    machine = AutonomousHealthStateMachine(
        policy=HealthStatePolicy(healthy_after=2),
        initial_state=AutonomousHealthState.DEGRADED,
    )

    machine.observe(healthy(40))
    report = machine.observe(unsafe(41))

    assert report.consecutive_healthy == 0
    assert report.consecutive_unhealthy == 1
    assert report.state is AutonomousHealthState.DEGRADED


def test_invalid_policy_is_rejected() -> None:
    try:
        HealthStatePolicy(degraded_after=2, halted_after=1)
    except ValueError as exc:
        assert "halted_after" in str(exc)
    else:
        raise AssertionError("invalid health policy was accepted")


def test_invalid_observation_timestamp_is_rejected() -> None:
    try:
        HealthObservation(True, True, True, True, False, 0)
    except ValueError as exc:
        assert "observed_at" in str(exc)
    else:
        raise AssertionError("invalid observation was accepted")
