from packages.promotion.canary_gate import CanaryGateReport


def test_clean_report_passes():
    report = CanaryGateReport()
    assert report.passed
    assert report.failures() == ()


def test_any_safety_failure_blocks_gate():
    failures = (
        "reconciliation_errors",
        "unresolved_unknowns",
        "balance_position_mismatches",
        "risk_violations",
        "critical_execution_errors",
    )
    for field in failures:
        assert not CanaryGateReport(**{field: 1}).passed


def test_operational_health_failures_block_gate():
    assert not CanaryGateReport(account_healthy=False).passed
    assert not CanaryGateReport(market_data_fresh=False).passed
    assert not CanaryGateReport(circuit_breaker_open=True).passed
    assert not CanaryGateReport(kill_switch=True).passed
