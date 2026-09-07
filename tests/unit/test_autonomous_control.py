import pytest

from packages.autonomy import AutonomousControl, AutonomousMode, AutonomousState


def test_default_control_is_fail_closed():
    control = AutonomousControl()

    assert control.mode is AutonomousMode.DISABLED
    assert control.state is AutonomousState.STOPPED
    assert not control.trading_enabled
    assert control.kill_switch_enabled
    assert not control.can_run()
    assert not control.can_open_position()


def test_start_requires_every_safety_prerequisite():
    control = (
        AutonomousControl()
        .with_mode(AutonomousMode.PAPER)
        .with_trading(True)
        .with_kill_switch(False)
    )

    running = control.start()

    assert running.state is AutonomousState.RUNNING
    assert running.can_run()
    assert running.can_open_position()


def test_start_rejects_disabled_mode():
    with pytest.raises(ValueError, match="disabled"):
        AutonomousControl().start()


def test_start_rejects_kill_switch():
    control = AutonomousControl().with_mode(AutonomousMode.PAPER).with_trading(True)

    with pytest.raises(ValueError, match="kill switch"):
        control.start()


def test_halt_forces_fail_closed_state():
    control = (
        AutonomousControl()
        .with_mode(AutonomousMode.TESTNET)
        .with_trading(True)
        .with_kill_switch(False)
        .start()
    )

    halted = control.halt()

    assert halted.state is AutonomousState.HALTED
    assert halted.kill_switch_enabled
    assert halted.circuit_breaker_open
    assert not halted.can_run()
    assert not halted.can_open_position()


def test_disabling_trading_stops_autonomy():
    control = (
        AutonomousControl()
        .with_mode(AutonomousMode.PAPER)
        .with_trading(True)
        .with_kill_switch(False)
        .start()
    )

    stopped = control.with_trading(False)

    assert stopped.state is AutonomousState.STOPPED
    assert not stopped.can_run()


def test_opening_circuit_breaker_halts_and_enables_kill_switch():
    control = (
        AutonomousControl()
        .with_mode(AutonomousMode.PAPER)
        .with_trading(True)
        .with_kill_switch(False)
        .start()
    )

    halted = control.with_circuit_breaker(True)

    assert halted.state is AutonomousState.HALTED
    assert halted.circuit_breaker_open
    assert halted.kill_switch_enabled
    assert not halted.can_run()
