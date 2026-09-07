from packages.autonomy.authorization_consumption import (
    AuthorizationConsumptionReport,
    AuthorizationConsumptionStatus,
)
from packages.autonomy.control import AutonomousControl, AutonomousMode, AutonomousState
from packages.autonomy.live_adapter import LiveAdapterPreflightContext
from packages.autonomy.live_runtime import (
    AutonomousLiveRuntimeGuard,
    LiveRuntimeConfig,
    LiveRuntimeMode,
)


def adapter_context() -> LiveAdapterPreflightContext:
    return LiveAdapterPreflightContext(
        endpoint="https://api.binance.com",
        credential_reference="secret/live-binance",
        account_enabled=True,
        healthcheck_passed=True,
    )


def authorization() -> AuthorizationConsumptionReport:
    return AuthorizationConsumptionReport(
        AuthorizationConsumptionStatus.AUTHORIZED,
        None,
        (),
    )


def running_live_control() -> AutonomousControl:
    return AutonomousControl(
        mode=AutonomousMode.LIVE,
        state=AutonomousState.RUNNING,
        trading_enabled=True,
        kill_switch_enabled=False,
        circuit_breaker_open=False,
    )


def test_defaults_are_fail_closed():
    config = LiveRuntimeConfig()
    report = AutonomousLiveRuntimeGuard().assess(
        config, running_live_control(), authorization(), adapter_context()
    )
    assert config.mode is LiveRuntimeMode.DISABLED
    assert not report.ready
    assert not report.submit_allowed
    assert "runtime_disabled" in report.reasons


def test_preflight_never_allows_submission():
    config = LiveRuntimeConfig(
        mode=LiveRuntimeMode.PREFLIGHT,
        execution_enabled=True,
        kill_switch=False,
    )
    report = AutonomousLiveRuntimeGuard().assess(
        config, running_live_control(), authorization(), adapter_context()
    )
    assert report.ready
    assert not report.submit_allowed


def test_dry_run_never_allows_submission():
    config = LiveRuntimeConfig(
        mode=LiveRuntimeMode.DRY_RUN,
        execution_enabled=True,
        kill_switch=False,
    )
    report = AutonomousLiveRuntimeGuard().assess(
        config, running_live_control(), authorization(), adapter_context()
    )
    assert report.ready
    assert not report.submit_allowed


def test_enabled_requires_explicit_execution_flag():
    config = LiveRuntimeConfig(
        mode=LiveRuntimeMode.ENABLED,
        execution_enabled=False,
        kill_switch=False,
    )
    report = AutonomousLiveRuntimeGuard().assess(
        config, running_live_control(), authorization(), adapter_context()
    )
    assert not report.submit_allowed
    assert "live_execution_not_explicitly_enabled" in report.reasons


def test_enabled_requires_authorization_and_running_control():
    config = LiveRuntimeConfig(
        mode=LiveRuntimeMode.ENABLED,
        execution_enabled=True,
        kill_switch=False,
    )
    blocked_auth = AuthorizationConsumptionReport(
        AuthorizationConsumptionStatus.BLOCKED,
        None,
        ("evidence_mismatch",),
    )
    stopped = AutonomousControl(mode=AutonomousMode.LIVE)
    report = AutonomousLiveRuntimeGuard().assess(config, stopped, blocked_auth, adapter_context())
    assert not report.submit_allowed
    assert "live_authorization_not_authorized" in report.reasons
    assert "autonomous_control_not_running" in report.reasons


def test_kill_switch_blocks_enabled_runtime():
    config = LiveRuntimeConfig(
        mode=LiveRuntimeMode.ENABLED,
        execution_enabled=True,
        kill_switch=True,
    )
    report = AutonomousLiveRuntimeGuard().assess(
        config, running_live_control(), authorization(), adapter_context()
    )
    assert not report.submit_allowed
    assert "deployment_kill_switch_enabled" in report.reasons


def test_environment_configuration_is_explicit_and_fail_closed():
    config = LiveRuntimeConfig.from_environment(
        {
            "LIVE_RUNTIME_MODE": "dry_run",
            "LIVE_EXECUTION_ENABLED": "false",
            "LIVE_KILL_SWITCH": "true",
        }
    )
    assert config.mode is LiveRuntimeMode.DRY_RUN
    assert not config.execution_enabled
    assert config.kill_switch


def test_invalid_environment_values_are_rejected():
    try:
        LiveRuntimeConfig.from_environment({"LIVE_RUNTIME_MODE": "production"})
    except ValueError as exc:
        assert "LIVE_RUNTIME_MODE" in str(exc)
    else:
        raise AssertionError("invalid runtime mode should fail closed")
