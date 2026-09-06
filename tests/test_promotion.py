from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from packages.promotion.canary import CanaryController, CanaryLimits, CanaryState
from packages.promotion.canary_gate import CanaryGateReport
from packages.promotion.domain import (
    ApprovalRole,
    CapitalAllocation,
    PromotionStage,
    PromotionStatus,
    StrategyVersion,
)
from packages.promotion.preflight import PreflightCode, PreflightContext, LivePreflight
from packages.promotion.service import PromotionService
from packages.trading.environment import EnvironmentGuard, TradingEnvironment


def version(fingerprint="a" * 64):
    return StrategyVersion(uuid4(), uuid4(), fingerprint, {"symbol": "BTCUSDT"})


def allocation(stage=PromotionStage.LIVE_CANARY):
    return CapitalAllocation(
        environment=stage,
        max_capital=Decimal("1000"),
        max_position_value=Decimal("200"),
        max_daily_loss=Decimal("50"),
        max_orders_per_day=20,
    )


def approved_promotion():
    service = PromotionService()
    p = service.request(
        strategy_version=version(), from_stage=PromotionStage.TESTNET,
        to_stage=PromotionStage.LIVE_CANARY, requested_by="operator",
        capital_allocation=allocation(), evidence={"testnet": "passed"},
    )
    service.approve(p, approver_id="risk-1", role=ApprovalRole.RISK_MANAGER, capital_limit=Decimal("1000"), evidence={"review": 1})
    service.approve(p, approver_id="admin-1", role=ApprovalRole.ADMIN, capital_limit=Decimal("1000"), evidence={"review": 2})
    return service, p


def test_live_requires_two_independent_roles():
    service = PromotionService()
    p = service.request(
        strategy_version=version(), from_stage=PromotionStage.TESTNET,
        to_stage=PromotionStage.LIVE_CANARY, requested_by="operator",
        capital_allocation=allocation(), evidence={"gate": True},
    )
    service.approve(p, approver_id="risk-1", role=ApprovalRole.RISK_MANAGER, capital_limit=Decimal("1000"), evidence={})
    assert p.status == PromotionStatus.PENDING
    with pytest.raises(PermissionError):
        service.activate(p)


def test_requester_cannot_approve():
    service = PromotionService()
    p = service.request(
        strategy_version=version(), from_stage=PromotionStage.TESTNET,
        to_stage=PromotionStage.LIVE_CANARY, requested_by="operator",
        capital_allocation=allocation(), evidence={},
    )
    with pytest.raises(PermissionError):
        service.approve(p, approver_id="operator", role=ApprovalRole.ADMIN, capital_limit=Decimal("1000"), evidence={})


def test_duplicate_approver_is_rejected():
    service, p = approved_promotion()
    with pytest.raises(ValueError):
        service.approve(p, approver_id="risk-1", role=ApprovalRole.RISK_MANAGER, capital_limit=Decimal("1000"), evidence={})


def test_mismatched_approval_fingerprint_is_rejected():
    service = PromotionService()
    p = service.request(
        strategy_version=version(), from_stage=PromotionStage.TESTNET,
        to_stage=PromotionStage.LIVE_CANARY, requested_by="operator",
        capital_allocation=allocation(), evidence={},
    )
    from packages.promotion.domain import Approval, ApprovalDecision
    bad = Approval("risk-1", ApprovalRole.RISK_MANAGER, ApprovalDecision.APPROVE, "b" * 64, Decimal("1000"), "e" * 64)
    with pytest.raises(ValueError):
        p.add_approval(bad)


def test_authorization_has_expiration_and_hash():
    service, p = approved_promotion()
    auth = service.authorization(p, risk_policy_fingerprint="r" * 64, ttl=timedelta(minutes=5))
    assert len(auth.authorization_hash) == 64
    assert auth.expires_at > auth.approvals[0].created_at


def test_authorization_cannot_bypass_fail_closed_live_environment_guard():
    service, p = approved_promotion()
    auth = service.authorization(p, risk_policy_fingerprint="r" * 64)
    assert auth.environment == PromotionStage.LIVE_CANARY
    with pytest.raises(PermissionError, match="fail-closed"):
        EnvironmentGuard.validate(TradingEnvironment.LIVE, EnvironmentGuard.LIVE_URL)


def test_authorization_requires_completed_approval():
    service = PromotionService()
    p = service.request(
        strategy_version=version(), from_stage=PromotionStage.TESTNET,
        to_stage=PromotionStage.LIVE_CANARY, requested_by="operator",
        capital_allocation=allocation(), evidence={},
    )
    with pytest.raises(PermissionError, match="not authorized"):
        service.authorization(p, risk_policy_fingerprint="r" * 64)


def test_preflight_fails_closed_on_kill_switch():
    service, p = approved_promotion()
    auth = service.authorization(p, risk_policy_fingerprint="r" * 64)
    context = PreflightContext(
        environment=PromotionStage.LIVE_CANARY,
        strategy_version_id=str(p.strategy_version.strategy_version_id),
        strategy_fingerprint=p.strategy_version.fingerprint,
        risk_policy_fingerprint="r" * 64,
        kill_switch=True, circuit_breaker_open=False, allocation_enabled=True,
        allocated_capital=Decimal("1000"), current_capital_usage=Decimal("0"),
        current_position_value=Decimal("0"), daily_loss=Decimal("0"),
        reconciliation_ok=True, account_healthy=True, market_data_fresh=True,
        exchange_base_url="https://api.binance.com",
    )
    result = LivePreflight().check(auth, context)
    assert not result.allowed
    assert PreflightCode.KILL_SWITCH in result.failures


def test_preflight_rejects_testnet_endpoint_for_live():
    service, p = approved_promotion()
    auth = service.authorization(p, risk_policy_fingerprint="r" * 64)
    context = PreflightContext(
        environment=PromotionStage.LIVE_CANARY,
        strategy_version_id=str(p.strategy_version.strategy_version_id),
        strategy_fingerprint=p.strategy_version.fingerprint,
        risk_policy_fingerprint="r" * 64,
        kill_switch=False, circuit_breaker_open=False, allocation_enabled=True,
        allocated_capital=Decimal("1000"), current_capital_usage=Decimal("0"),
        current_position_value=Decimal("0"), daily_loss=Decimal("0"),
        reconciliation_ok=True, account_healthy=True, market_data_fresh=True,
        exchange_base_url="https://testnet.binance.vision",
    )
    result = LivePreflight().check(auth, context)
    assert PreflightCode.EXCHANGE_ENDPOINT_INVALID in result.failures


def test_environment_guard_live_requires_explicit_arm():
    with pytest.raises(PermissionError):
        EnvironmentGuard.validate(TradingEnvironment.LIVE, EnvironmentGuard.LIVE_URL)


def test_environment_guard_rejects_live_endpoint_in_testnet():
    with pytest.raises(RuntimeError):
        EnvironmentGuard.validate(TradingEnvironment.TESTNET, EnvironmentGuard.LIVE_URL)


def test_canary_cannot_exceed_approved_allocation():
    service, p = approved_promotion()
    canary = CanaryController()
    with pytest.raises(ValueError):
        canary.arm(p, CanaryLimits(Decimal("1001"), Decimal("200"), Decimal("50"), 20), authorization_hash="a" * 64)


def test_canary_requires_clean_gate_for_activation():
    service, p = approved_promotion()
    canary = CanaryController()
    canary.arm(p, CanaryLimits(Decimal("100"), Decimal("50"), Decimal("10"), 5), authorization_hash="a" * 64)
    failed = CanaryGateReport(reconciliation_errors=1)
    with pytest.raises(PermissionError, match="reconciliation"):
        canary.start(p, gate=failed)
    assert canary.state == CanaryState.ARMED


def test_canary_activation_records_passed_gate():
    service, p = approved_promotion()
    canary = CanaryController()
    canary.arm(p, CanaryLimits(Decimal("100"), Decimal("50"), Decimal("10"), 5), authorization_hash="a" * 64)
    gate = CanaryGateReport()
    canary.start(p, gate=gate)
    assert canary.state == CanaryState.ACTIVE
    assert canary.last_gate == gate
    assert canary.authorization_hash == "a" * 64


def test_canary_gate_required_for_scaling():
    service, p = approved_promotion()
    canary = CanaryController()
    canary.arm(p, CanaryLimits(Decimal("100"), Decimal("50"), Decimal("10"), 5), authorization_hash="a" * 64)
    canary.start(p, gate=CanaryGateReport())
    with pytest.raises(PermissionError):
        canary.scale(new_limits=CanaryLimits(Decimal("200"), Decimal("100"), Decimal("20"), 10), canary_gate=CanaryGateReport(risk_violations=1))
    canary.scale(new_limits=CanaryLimits(Decimal("200"), Decimal("100"), Decimal("20"), 10), canary_gate=CanaryGateReport())
    assert canary.state == CanaryState.ACTIVE


def test_canary_gate_reports_all_failed_conditions():
    report = CanaryGateReport(
        reconciliation_errors=1,
        unresolved_unknowns=1,
        balance_position_mismatches=1,
        risk_violations=1,
        critical_execution_errors=1,
        account_healthy=False,
        market_data_fresh=False,
        circuit_breaker_open=True,
        kill_switch=True,
    )
    assert not report.passed
    assert len(report.failures()) == 9
