from packages.autonomy.live_adapter import (
    AutonomousLiveAdapterPreflight,
    LiveAdapterPreflightContext,
    LiveAdapterStatus,
)


def healthy() -> LiveAdapterPreflightContext:
    return LiveAdapterPreflightContext(
        endpoint="https://api.binance.com",
        credential_reference="secret-manager://binance/live",
        account_enabled=True,
        healthcheck_passed=True,
    )


def test_healthy_production_adapter_is_ready() -> None:
    report = AutonomousLiveAdapterPreflight().assess(healthy())
    assert report.status is LiveAdapterStatus.READY


def test_testnet_endpoint_is_blocked() -> None:
    context = LiveAdapterPreflightContext(
        "https://testnet.binance.vision",
        "secret-manager://binance/testnet",
        True,
        True,
    )
    report = AutonomousLiveAdapterPreflight().assess(context)
    assert report.status is LiveAdapterStatus.BLOCKED
    assert "endpoint_not_approved" in report.reasons
    assert "test_environment_not_allowed" in report.reasons


def test_missing_credential_reference_is_blocked() -> None:
    context = healthy()
    context = LiveAdapterPreflightContext(
        context.endpoint,
        "",
        context.account_enabled,
        context.healthcheck_passed,
    )
    report = AutonomousLiveAdapterPreflight().assess(context)
    assert report.status is LiveAdapterStatus.BLOCKED
    assert "credential_reference_missing" in report.reasons


def test_disabled_account_is_blocked() -> None:
    context = healthy()
    context = LiveAdapterPreflightContext(
        context.endpoint,
        context.credential_reference,
        False,
        context.healthcheck_passed,
    )
    report = AutonomousLiveAdapterPreflight().assess(context)
    assert report.status is LiveAdapterStatus.BLOCKED
    assert "account_disabled" in report.reasons


def test_failed_healthcheck_is_blocked() -> None:
    context = healthy()
    context = LiveAdapterPreflightContext(
        context.endpoint,
        context.credential_reference,
        context.account_enabled,
        False,
    )
    report = AutonomousLiveAdapterPreflight().assess(context)
    assert report.status is LiveAdapterStatus.BLOCKED
    assert "adapter_healthcheck_failed" in report.reasons
