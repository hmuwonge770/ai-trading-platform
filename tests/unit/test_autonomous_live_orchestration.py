from types import SimpleNamespace
from unittest.mock import Mock

from packages.autonomy.authorization_consumption import AuthorizationConsumptionStatus
from packages.autonomy.control import AutonomousControl, AutonomousMode, AutonomousState
from packages.autonomy.live_adapter import LiveAdapterPreflightContext
from packages.autonomy.live_execution import LiveExecutionReport, LiveExecutionStatus
from packages.autonomy.live_orchestration import AutonomousLiveRuntimeOrchestrator, LiveOrchestrationStatus
from packages.autonomy.live_runtime import AutonomousLiveRuntimeGuard, LiveRuntimeConfig, LiveRuntimeMode


def _control() -> AutonomousControl:
    return AutonomousControl(
        mode=AutonomousMode.LIVE, state=AutonomousState.RUNNING,
        trading_enabled=True, kill_switch_enabled=False, circuit_breaker_open=False,
    )


def _authorization(status=AuthorizationConsumptionStatus.AUTHORIZED):
    return SimpleNamespace(status=status)


def _adapter() -> LiveAdapterPreflightContext:
    return LiveAdapterPreflightContext(
        endpoint="https://api.binance.com", credential_reference="secret/live/binance",
        account_enabled=True, healthcheck_passed=True,
    )


def _risk() -> SimpleNamespace:
    return SimpleNamespace(approved=True, order=SimpleNamespace(client_order_id="client-1"))


def _orchestrator(boundary: Mock) -> AutonomousLiveRuntimeOrchestrator:
    return AutonomousLiveRuntimeOrchestrator(
        runtime_guard=AutonomousLiveRuntimeGuard(), execution_boundary=boundary,
    )


def test_disabled_runtime_never_reaches_execution_boundary():
    boundary = Mock()
    report = _orchestrator(boundary).execute(
        config=LiveRuntimeConfig(), control=_control(), authorization=_authorization(),
        authorization_snapshot=object(), risk_result=_risk(), adapter=_adapter(),
    )
    assert report.status is LiveOrchestrationStatus.BLOCKED
    boundary.submit.assert_not_called()


def test_preflight_and_dry_run_never_submit():
    boundary = Mock()
    orchestrator = _orchestrator(boundary)
    for mode, expected in (
        (LiveRuntimeMode.PREFLIGHT, LiveOrchestrationStatus.PREFLIGHT),
        (LiveRuntimeMode.DRY_RUN, LiveOrchestrationStatus.DRY_RUN),
    ):
        report = orchestrator.execute(
            config=LiveRuntimeConfig(mode=mode), control=_control(), authorization=_authorization(),
            authorization_snapshot=object(), risk_result=_risk(), adapter=_adapter(),
        )
        assert report.status is expected
    boundary.submit.assert_not_called()


def test_authorization_failure_never_submits():
    boundary = Mock()
    report = _orchestrator(boundary).execute(
        config=LiveRuntimeConfig(mode=LiveRuntimeMode.ENABLED, execution_enabled=True, kill_switch=False),
        control=_control(), authorization=_authorization(AuthorizationConsumptionStatus.BLOCKED),
        authorization_snapshot=object(), risk_result=_risk(), adapter=_adapter(),
    )
    assert report.status is LiveOrchestrationStatus.BLOCKED
    boundary.submit.assert_not_called()


def test_enabled_runtime_delegates_exactly_once():
    boundary = Mock()
    boundary.submit.return_value = LiveExecutionReport(
        LiveExecutionStatus.SUBMITTED, "client-1", {"ok": True}, (),
    )
    orchestrator = _orchestrator(boundary)
    snapshot = object()
    risk = _risk()
    report = orchestrator.execute(
        config=LiveRuntimeConfig(mode=LiveRuntimeMode.ENABLED, execution_enabled=True, kill_switch=False),
        control=_control(), authorization=_authorization(), authorization_snapshot=snapshot,
        risk_result=risk, adapter=_adapter(),
    )
    assert report.status is LiveOrchestrationStatus.SUBMITTED
    boundary.submit.assert_called_once_with(
        authorization=snapshot, risk_result=risk, control=_control(),
    )


def test_enabled_runtime_requires_authorization_snapshot():
    boundary = Mock()
    report = _orchestrator(boundary).execute(
        config=LiveRuntimeConfig(mode=LiveRuntimeMode.ENABLED, execution_enabled=True, kill_switch=False),
        control=_control(), authorization=_authorization(), authorization_snapshot=None,
        risk_result=_risk(), adapter=_adapter(),
    )
    assert report.status is LiveOrchestrationStatus.BLOCKED
    assert "live_authorization_snapshot_missing" in report.reasons
    boundary.submit.assert_not_called()
