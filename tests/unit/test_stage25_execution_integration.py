from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from packages.execution import (
    AuthorizationStore,
    ExecutionConfig,
    ExecutionSimulator,
    ExecutionService,
    PromotionExecutionGateway,
)
from packages.promotion import AuthorizationRecord, PromotionStatus, PromotionStage
from packages.risk import RiskDecision, RiskReason
from packages.strategies.models import MarketBar, Signal
from packages.trading.environment import EnvironmentGuard
from packages.trading.paper import OrderIntent


STRATEGY_VERSION_ID = uuid4()
STRATEGY_FINGERPRINT = "a" * 64
RISK_FINGERPRINT = "b" * 64
AUTH_HASH = "c" * 64
NOW = datetime(2026, 9, 6, 12, 0, tzinfo=timezone.utc)


def order() -> OrderIntent:
    return OrderIntent(
        intent_id=uuid4(), signal_id=uuid4(), strategy_version_id=str(STRATEGY_VERSION_ID),
        symbol="BTCUSDT", timeframe="1m", side=Signal.BUY, quantity=Decimal("1"),
        reference_price=Decimal("100"), client_order_id="client-25", reason="test",
    )


def candle() -> MarketBar:
    return MarketBar(
        symbol="BTCUSDT", timeframe="1m", open_time=NOW,
        open=Decimal("100"), high=Decimal("101"), low=Decimal("99"),
        close=Decimal("100"), volume=Decimal("10"),
    )


def risk() -> RiskDecision:
    return RiskDecision(
        approved=True, reason=RiskReason.APPROVED, message="approved",
        order_id="client-25", order_notional=Decimal("100"),
        projected_position_notional=Decimal("100"), projected_total_exposure=Decimal("100"),
    )


def store(status=PromotionStatus.ACTIVE, expires=NOW + timedelta(minutes=10)) -> AuthorizationStore:
    record = AuthorizationRecord(
        authorization_hash=AUTH_HASH, promotion_status=status,
        strategy_version_id=STRATEGY_VERSION_ID, strategy_fingerprint=STRATEGY_FINGERPRINT,
        environment=PromotionStage.LIVE_CANARY, risk_policy_fingerprint=RISK_FINGERPRINT,
        expires_at=expires,
    )
    return AuthorizationStore(lambda _: record)


def gateway(status=PromotionStatus.ACTIVE, expires=NOW + timedelta(minutes=10)) -> PromotionExecutionGateway:
    return PromotionExecutionGateway(
        ExecutionService(ExecutionSimulator(ExecutionConfig())), store(status, expires)
    )


def test_active_authorization_risk_and_environment_are_required_before_execution():
    result = gateway().submit(
        order(), risk(), candle(), authorization_hash=AUTH_HASH,
        risk_policy_fingerprint=RISK_FINGERPRINT,
        exchange_url=EnvironmentGuard.LIVE_URL, live_armed=True, now=NOW,
    )
    assert result.accepted is True
    assert result.fill is not None


def test_halted_promotion_cannot_execute():
    result = gateway(PromotionStatus.HALTED).submit(
        order(), risk(), candle(), authorization_hash=AUTH_HASH,
        risk_policy_fingerprint=RISK_FINGERPRINT,
        exchange_url=EnvironmentGuard.LIVE_URL, live_armed=True, now=NOW,
    )
    assert result.accepted is False
    assert "authorization" in result.reason


def test_expired_authorization_cannot_execute():
    result = gateway(expires=NOW).submit(
        order(), risk(), candle(), authorization_hash=AUTH_HASH,
        risk_policy_fingerprint=RISK_FINGERPRINT,
        exchange_url=EnvironmentGuard.LIVE_URL, live_armed=True, now=NOW,
    )
    assert result.accepted is False


def test_live_environment_remains_fail_closed_without_explicit_arm():
    result = gateway().submit(
        order(), risk(), candle(), authorization_hash=AUTH_HASH,
        risk_policy_fingerprint=RISK_FINGERPRINT,
        exchange_url=EnvironmentGuard.LIVE_URL, live_armed=False, now=NOW,
    )
    assert result.accepted is False
    assert "armed" in result.reason


def test_mismatched_risk_policy_cannot_execute():
    result = gateway().submit(
        order(), risk(), candle(), authorization_hash=AUTH_HASH,
        risk_policy_fingerprint="d" * 64,
        exchange_url=EnvironmentGuard.LIVE_URL, live_armed=True, now=NOW,
    )
    assert result.accepted is False
    assert "risk policy" in result.reason


def test_mismatched_strategy_version_cannot_execute():
    bad_order = OrderIntent(
        intent_id=uuid4(), signal_id=uuid4(), strategy_version_id=str(uuid4()),
        symbol="BTCUSDT", timeframe="1m", side=Signal.BUY, quantity=Decimal("1"),
        reference_price=Decimal("100"), client_order_id="client-25-bad", reason="test",
    )
    result = gateway().submit(
        bad_order, risk(), candle(), authorization_hash=AUTH_HASH,
        risk_policy_fingerprint=RISK_FINGERPRINT,
        exchange_url=EnvironmentGuard.LIVE_URL, live_armed=True, now=NOW,
    )
    assert result.accepted is False
    assert "strategy version" in result.reason
