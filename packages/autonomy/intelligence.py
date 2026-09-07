"""AI-assisted market regime and signal intelligence.

The intelligence layer is advisory only. It normalizes model output into a
small typed contract and applies deterministic freshness, symbol, confidence,
and regime compatibility checks before an existing decision can be emitted.
No exchange transport, credentials, sizing, or order submission belongs here.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Protocol

from packages.autonomy.decision import Decision, DecisionAction, MarketSnapshot


class MarketRegime(StrEnum):
    TREND_UP = "TREND_UP"
    TREND_DOWN = "TREND_DOWN"
    RANGE = "RANGE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class RegimeAssessment:
    regime: MarketRegime
    confidence: Decimal
    reason: str


@dataclass(frozen=True, slots=True)
class AISignalProposal:
    """Untrusted, structured model output awaiting deterministic validation."""

    action: DecisionAction
    symbol: str
    confidence: Decimal
    rationale: str
    evidence: tuple[str, ...]
    issued_at: int
    expires_at: int

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol is required")
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        if not self.rationale.strip():
            raise ValueError("rationale is required")
        if len(self.evidence) > 10:
            raise ValueError("at most 10 evidence references are allowed")
        if self.issued_at <= 0 or self.expires_at <= self.issued_at:
            raise ValueError("signal expiry must be after issuance")


class AISignalModel(Protocol):
    """Provider-neutral AI boundary; implementations receive no secrets."""

    def propose(self, snapshot: MarketSnapshot, regime: RegimeAssessment) -> AISignalProposal:
        ...


class DeterministicRegimeDetector:
    """Classify the current market using bounded, deterministic features."""

    def assess(self, snapshot: MarketSnapshot) -> RegimeAssessment:
        if snapshot.ema_fast > snapshot.ema_slow:
            return RegimeAssessment(
                MarketRegime.TREND_UP,
                Decimal("0.80"),
                "fast EMA is above slow EMA",
            )
        if snapshot.ema_fast < snapshot.ema_slow:
            return RegimeAssessment(
                MarketRegime.TREND_DOWN,
                Decimal("0.80"),
                "fast EMA is below slow EMA",
            )
        return RegimeAssessment(
            MarketRegime.RANGE,
            Decimal("0.60"),
            "fast and slow EMA are equal",
        )


@dataclass(frozen=True, slots=True)
class IntelligencePolicy:
    min_confidence: Decimal = Decimal("0.70")
    max_signal_age_seconds: int = 60

    def __post_init__(self) -> None:
        if not 0 < self.min_confidence <= 1:
            raise ValueError("min_confidence must be in (0, 1]")
        if self.max_signal_age_seconds <= 0:
            raise ValueError("max_signal_age_seconds must be positive")


class AutonomousMarketIntelligence:
    """Turn AI advice into a bounded decision without granting execution power."""

    def __init__(
        self,
        model: AISignalModel,
        *,
        regime_detector: DeterministicRegimeDetector | None = None,
        policy: IntelligencePolicy | None = None,
    ) -> None:
        self._model = model
        self._regime_detector = regime_detector or DeterministicRegimeDetector()
        self.policy = policy or IntelligencePolicy()

    def evaluate(self, snapshot: MarketSnapshot, *, now: int) -> Decision:
        regime = self._regime_detector.assess(snapshot)
        proposal = self._model.propose(snapshot, regime)
        self._validate(snapshot, proposal, regime, now)

        if proposal.expires_at <= now:
            return self._hold(snapshot, "AI signal has expired")
        if proposal.confidence < self.policy.min_confidence:
            return self._hold(snapshot, "AI signal confidence is below the threshold")
        if proposal.action == DecisionAction.BUY and regime.regime == MarketRegime.TREND_DOWN:
            return self._hold(snapshot, "AI BUY conflicts with the detected downtrend")
        if proposal.action == DecisionAction.SELL and regime.regime == MarketRegime.TREND_UP:
            return self._hold(snapshot, "AI SELL conflicts with the detected uptrend")

        return Decision(
            proposal.action,
            snapshot.symbol,
            proposal.confidence,
            proposal.rationale,
            snapshot.timestamp,
        )

    def _validate(
        self,
        snapshot: MarketSnapshot,
        proposal: AISignalProposal,
        regime: RegimeAssessment,
        now: int,
    ) -> None:
        if proposal.symbol != snapshot.symbol:
            raise ValueError("AI signal symbol does not match market snapshot")
        if proposal.issued_at > now:
            raise ValueError("AI signal cannot be issued in the future")
        if now - proposal.issued_at > self.policy.max_signal_age_seconds:
            raise ValueError("AI signal is too old")
        if not isinstance(proposal.action, DecisionAction):
            raise ValueError("unsupported AI decision action")
        if regime.regime is MarketRegime.UNKNOWN:
            raise ValueError("unknown market regime")

    @staticmethod
    def _hold(snapshot: MarketSnapshot, reason: str) -> Decision:
        return Decision(
            DecisionAction.HOLD,
            snapshot.symbol,
            Decimal("0"),
            reason,
            snapshot.timestamp,
        )
