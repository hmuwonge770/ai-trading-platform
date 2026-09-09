from packages.autonomy.security_hardening import (
    SecurityHardeningPolicy,
    SecurityObservation,
    SecurityStatus,
    assess_security,
)


def secure_observation() -> SecurityObservation:
    return SecurityObservation(True, True, True, True, True, True)


def test_secure_when_all_required_controls_are_verified():
    report = assess_security(SecurityHardeningPolicy(), secure_observation())
    assert report.status is SecurityStatus.SECURE
    assert report.reasons == ()


def test_missing_secret_isolation_blocks():
    report = assess_security(SecurityHardeningPolicy(), SecurityObservation(False, True, True, True, True, True))
    assert report.status is SecurityStatus.BLOCKED
    assert "secret_isolation_failed" in report.reasons


def test_identity_failure_blocks_even_when_controls_are_secure():
    report = assess_security(SecurityHardeningPolicy(), SecurityObservation(True, True, True, True, True, False))
    assert report.status is SecurityStatus.BLOCKED
    assert report.reasons == ("identity_verification_failed",)


def test_all_failed_controls_are_reported_deterministically():
    observation = SecurityObservation(False, False, False, False, False, False)
    expected = (
        "identity_verification_failed",
        "secret_isolation_failed",
        "strategy_artifact_verification_failed",
        "audit_integrity_failed",
        "dependency_integrity_failed",
        "operator_shutdown_unavailable",
    )
    first = assess_security(SecurityHardeningPolicy(), observation)
    second = assess_security(SecurityHardeningPolicy(), observation)
    assert first == second
    assert first.status is SecurityStatus.BLOCKED
    assert first.reasons == expected


def test_optional_policy_checks_can_be_disabled_but_identity_remains_required():
    policy = SecurityHardeningPolicy(False, False, False, False, False)
    report = assess_security(policy, SecurityObservation(False, False, False, False, False, True))
    assert report.status is SecurityStatus.SECURE
