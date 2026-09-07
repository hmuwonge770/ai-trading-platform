from decimal import Decimal

from packages.autonomy.decision import Decision, DecisionAction
from packages.autonomy.risk import AutonomousRiskEngine, AutonomousRiskPolicy
from packages.portfolio import PortfolioSnapshot
from packages.risk.gateway import RiskGateway, RiskLimits, RiskReason


def portfolio(cash: str = "10000") -> PortfolioSnapshot:
    return PortfolioSnapshot(
        base_currency="USDT",
        available_cash=Decimal(cash),
        reserved_cash=Decimal("0"),
        positions=(),
        realized_pnl=Decimal("0"),
        total_fees=Decimal("0"),
    )


def decision(action: DecisionAction = DecisionAction.BUY, timestamp: int = 1_000) -> Decision:
    return Decision(
        action=action,
        symbol="BTCUSDT",
        confidence=Decimal("0.90"),
        reason="validated autonomous signal",
        timestamp=timestamp,
    )


def engine(*, policy: AutonomousRiskPolicy | None = None) -> AutonomousRiskEngine:
    gateway = RiskGateway(
        RiskLimits(
            max_order_notional=Decimal("1000"),
            max_position_notional=Decimal("2000"),
            max_total_exposure=Decimal("3000"),
            max_daily_loss=Decimal("500"),
            min_cash_after_order=Decimal("100"),
        )
    )
    return AutonomousRiskEngine(gateway, policy=policy, clock=lambda: 1_000)


def evaluate(engine_instance: AutonomousRiskEngine, **kwargs):
    return engine_instance.evaluate(
        decision(),
        quantity=Decimal("2"),
        timeframe="1m",
        strategy_version_id="strategy-v1",
        portfolio=portfolio(),
        current_price=Decimal("100"),
        total_exposure=Decimal("0"),
        daily_realized_pnl=Decimal("0"),
        liquidity_quote_volume=Decimal("5000"),
        now=1_000,
        **kwargs,
    )


def test_valid_decision_passes_autonomous_and_gateway_risk() -> None:
    result = evaluate(engine())

    assert result.approved is True
    assert result.reason == "approved"
    assert result.order is not None
    assert result.gateway_decision is not None
    assert result.gateway_decision.reason is RiskReason.APPROVED


def test_hold_never_becomes_an_order() -> None:
    risk_engine = engine()
    result = risk_engine.evaluate(
        decision(DecisionAction.HOLD),
        quantity=Decimal("2"),
        timeframe="1m",
        strategy_version_id="strategy-v1",
        portfolio=portfolio(),
        current_price=Decimal("100"),
        total_exposure=Decimal("0"),
        daily_realized_pnl=Decimal("0"),
        liquidity_quote_volume=Decimal("5000"),
        now=1_000,
    )

    assert result.approved is False
    assert result.order is None


def test_stale_decision_is_rejected() -> None:
    risk_engine = engine()
    result = risk_engine.evaluate(
        decision(timestamp=900),
        quantity=Decimal("2"),
        timeframe="1m",
        strategy_version_id="strategy-v1",
        portfolio=portfolio(),
        current_price=Decimal("100"),
        total_exposure=Decimal("0"),
        daily_realized_pnl=Decimal("0"),
        liquidity_quote_volume=Decimal("5000"),
        now=1_000,
    )

    assert result.approved is False
    assert result.reason == "stale_decision"


def test_liquidity_fraction_is_enforced_before_gateway() -> None:
    result = evaluate(engine())
    assert result.approved is True

    risk_engine = engine()
    result = risk_engine.evaluate(
        decision(),
        quantity=Decimal("2"),
        timeframe="1m",
        strategy_version_id="strategy-v1",
        portfolio=portfolio(),
        current_price=Decimal("100"),
        total_exposure=Decimal("0"),
        daily_realized_pnl=Decimal("0"),
        liquidity_quote_volume=Decimal("1500"),
        now=1_000,
    )

    assert result.approved is False
    assert result.reason == "liquidity_limit"


def test_order_rate_limit_is_enforced() -> None:
    risk_engine = engine(
        policy=AutonomousRiskPolicy(
            max_orders_per_window=1,
            order_window_seconds=60,
            max_decision_age_seconds=60,
            max_liquidity_fraction=Decimal("0.10"),
        )
    )

    first = evaluate(risk_engine)
    second = evaluate(risk_engine)

    assert first.approved is True
    assert second.approved is False
    assert second.reason == "order_rate_limit"


def test_existing_gateway_rejection_remains_final() -> None:
    risk_engine = engine()
    result = risk_engine.evaluate(
        decision(),
        quantity=Decimal("20"),
        timeframe="1m",
        strategy_version_id="strategy-v1",
        portfolio=portfolio(),
        current_price=Decimal("100"),
        total_exposure=Decimal("0"),
        daily_realized_pnl=Decimal("0"),
        liquidity_quote_volume=Decimal("50000"),
        now=1_000,
    )

    assert result.approved is False
    assert result.reason == "gateway_rejected"
    assert result.gateway_decision is not None
    assert result.gateway_decision.reason is RiskReason.ORDER_NOTIONAL_LIMIT
