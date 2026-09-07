from decimal import Decimal

import pytest

from packages.autonomy.decision import DecisionAction, MarketSnapshot
from packages.autonomy.intelligence import (
    AISignalProposal,
    AutonomousMarketIntelligence,
    DeterministicRegimeDetector,
    IntelligencePolicy,
    MarketRegime,
    RegimeAssessment,
)


class FakeSignalModel:
    def __init__(self, proposal: AISignalProposal) -> None:
        self.proposal = proposal
        self.regime: RegimeAssessment | None = None

    def propose(self, snapshot: MarketSnapshot, regime: RegimeAssessment) -> AISignalProposal:
        self.regime = regime
        return self.proposal


def snapshot(*, fast: str = "101", slow: str = "100") -> MarketSnapshot:
    return MarketSnapshot(
        symbol="BTCUSDT",
        price=Decimal("100"),
        ema_fast=Decimal(fast),
        ema_slow=Decimal(slow),
        rsi=Decimal("50"),
        timestamp=1_000,
    )


def proposal(
    *,
    action: DecisionAction = DecisionAction.BUY,
    symbol: str = "BTCUSDT",
    confidence: str = "0.90",
    issued_at: int = 990,
    expires_at: int = 1_050,
) -> AISignalProposal:
    return AISignalProposal(
        action=action,
        symbol=symbol,
        confidence=Decimal(confidence),
        rationale="The current evidence supports the proposed directional signal.",
        evidence=("ema_alignment", "rsi_context"),
        issued_at=issued_at,
        expires_at=expires_at,
    )


def test_regime_detector_is_deterministic() -> None:
    detector = DeterministicRegimeDetector()

    assert detector.assess(snapshot()).regime is MarketRegime.TREND_UP
    assert detector.assess(snapshot(fast="99", slow="100")).regime is MarketRegime.TREND_DOWN
    assert detector.assess(snapshot(fast="100", slow="100")).regime is MarketRegime.RANGE


def test_valid_ai_signal_becomes_decision() -> None:
    model = FakeSignalModel(proposal())
    intelligence = AutonomousMarketIntelligence(model)

    decision = intelligence.evaluate(snapshot(), now=1_000)

    assert decision.action is DecisionAction.BUY
    assert decision.confidence == Decimal("0.90")
    assert model.regime is not None
    assert model.regime.regime is MarketRegime.TREND_UP


def test_expired_signal_fails_closed_to_hold() -> None:
    model = FakeSignalModel(proposal(expires_at=999))
    intelligence = AutonomousMarketIntelligence(model)

    decision = intelligence.evaluate(snapshot(), now=1_000)

    assert decision.action is DecisionAction.HOLD
    assert "expired" in decision.reason


def test_low_confidence_signal_fails_closed_to_hold() -> None:
    model = FakeSignalModel(proposal(confidence="0.69"))
    intelligence = AutonomousMarketIntelligence(model)

    decision = intelligence.evaluate(snapshot(), now=1_000)

    assert decision.action is DecisionAction.HOLD
    assert "confidence" in decision.reason


def test_buy_conflicting_with_downtrend_fails_closed() -> None:
    model = FakeSignalModel(proposal(action=DecisionAction.BUY))
    intelligence = AutonomousMarketIntelligence(model)

    decision = intelligence.evaluate(snapshot(fast="99", slow="100"), now=1_000)

    assert decision.action is DecisionAction.HOLD
    assert "downtrend" in decision.reason


def test_sell_conflicting_with_uptrend_fails_closed() -> None:
    model = FakeSignalModel(proposal(action=DecisionAction.SELL))
    intelligence = AutonomousMarketIntelligence(model)

    decision = intelligence.evaluate(snapshot(), now=1_000)

    assert decision.action is DecisionAction.HOLD
    assert "uptrend" in decision.reason


def test_wrong_symbol_is_rejected() -> None:
    model = FakeSignalModel(proposal(symbol="ETHUSDT"))
    intelligence = AutonomousMarketIntelligence(model)

    with pytest.raises(ValueError, match="symbol"):
        intelligence.evaluate(snapshot(), now=1_000)


def test_stale_signal_is_rejected() -> None:
    model = FakeSignalModel(proposal(issued_at=900))
    intelligence = AutonomousMarketIntelligence(
        model,
        policy=IntelligencePolicy(max_signal_age_seconds=50),
    )

    with pytest.raises(ValueError, match="too old"):
        intelligence.evaluate(snapshot(), now=1_000)


def test_future_signal_is_rejected() -> None:
    model = FakeSignalModel(proposal(issued_at=1_001))
    intelligence = AutonomousMarketIntelligence(model)

    with pytest.raises(ValueError, match="future"):
        intelligence.evaluate(snapshot(), now=1_000)
