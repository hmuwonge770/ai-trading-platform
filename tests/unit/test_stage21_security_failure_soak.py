from decimal import Decimal

import pytest

from packages.accounting import AccountingEntry, AccountingTransaction, Ledger
from packages.reliability import FailurePlan, InjectedFailure
from packages.security import CredentialRedactor, SecurityPolicy
from packages.trading.environment import EnvironmentGuard, TradingEnvironment


def test_research_context_rejects_credentials() -> None:
    with pytest.raises(PermissionError, match="research context"):
        SecurityPolicy().validate_research_context({"symbol": "BTCUSDT", "api_secret": "never-log-this"})


def test_security_policy_rejects_live_by_default() -> None:
    with pytest.raises(PermissionError, match="live execution is disabled"):
        SecurityPolicy().validate_endpoint(SecurityEnvironment.LIVE, "https://api.binance.com")


def test_security_policy_rejects_testnet_wrong_endpoint() -> None:
    with pytest.raises(PermissionError, match="Spot Testnet"):
        SecurityPolicy().validate_endpoint(SecurityEnvironment.TESTNET, "https://api.binance.com")


def test_existing_environment_guard_remains_fail_closed() -> None:
    with pytest.raises(PermissionError, match="fail-closed"):
        EnvironmentGuard.validate(TradingEnvironment.LIVE, EnvironmentGuard.LIVE_URL)


def test_redactor_removes_secret_values() -> None:
    payload = CredentialRedactor.redact_mapping({"symbol": "BTCUSDT", "api_secret": "secret-value"})
    assert payload == {"symbol": "BTCUSDT", "api_secret": "[REDACTED]"}
    assert "secret-value" not in CredentialRedactor.redact_text("api_secret=secret-value&symbol=BTCUSDT")


def test_failure_plan_is_deterministic_and_counted() -> None:
    plan = FailurePlan(fail_on=frozenset({2, 4}))
    plan.checkpoint("publish")
    with pytest.raises(InjectedFailure):
        plan.checkpoint("publish")
    plan.checkpoint("publish")
    with pytest.raises(InjectedFailure):
        plan.checkpoint("publish")
    assert plan.calls == 4


def test_ledger_post_is_idempotent_under_repeated_delivery() -> None:
    ledger = Ledger()
    tx = AccountingTransaction(
        reference="soak-1",
        transaction_type="deposit",
        entries=(
            AccountingEntry(account="cash", asset="USDT", debit=Decimal("100")),
            AccountingEntry(account="equity", asset="USDT", credit=Decimal("100")),
        ),
    )
    first = ledger.post(tx)
    for _ in range(1000):
        assert ledger.post(tx) == first
    assert ledger.balance("cash", "USDT").debit == Decimal("100")


def test_failure_soak_does_not_hide_later_failures() -> None:
    plan = FailurePlan(fail_on=frozenset({7, 19, 31, 43}))
    failures = 0
    for _ in range(50):
        try:
            plan.checkpoint("consumer")
        except InjectedFailure:
            failures += 1
    assert failures == 4
    assert plan.calls == 50
