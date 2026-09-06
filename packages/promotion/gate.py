from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4


class PromotionTarget(StrEnum):
    PAPER = "paper"
    TESTNET = "testnet"
    LIVE = "live"


@dataclass(frozen=True, slots=True)
class PromotionEvidence:
    """Immutable evidence required before advancing a strategy lifecycle."""

    strategy_fingerprint: str
    dataset_fingerprint: str
    research_gate_passed: bool = False
    paper_trading_passed: bool = False
    testnet_passed: bool = False
    risk_limits_fingerprint: str | None = None
    paper_run_id: str | None = None
    testnet_run_id: str | None = None

    def __post_init__(self) -> None:
        for name in ("strategy_fingerprint", "dataset_fingerprint"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must not be empty")
        if self.paper_trading_passed and not self.paper_run_id:
            raise ValueError("paper_run_id is required when paper trading has passed")
        if self.testnet_passed and not self.testnet_run_id:
            raise ValueError("testnet_run_id is required when testnet has passed")
        if self.testnet_passed and not self.paper_trading_passed:
            raise ValueError("testnet evidence requires passed paper trading evidence")


@dataclass(frozen=True, slots=True)
class AuthorizationDecision:
    """Immutable result of a promotion decision; it does not execute trades."""

    authorization_id: UUID
    approved: bool
    target: PromotionTarget
    reason: str
    strategy_fingerprint: str
    dataset_fingerprint: str
    authorized_by: str | None = None
    issued_at: datetime | None = None


class PromotionGate:
    """Fail-closed lifecycle gate between research and execution environments.

    Promotion is evidence-driven and deterministic. Live authorization is an
    explicit human authorization record only; it does not enable the exchange
    client or bypass the separate security/environment guards.
    """

    @staticmethod
    def evaluate(
        target: PromotionTarget,
        evidence: PromotionEvidence,
        *,
        authorized_by: str | None = None,
        explicit_live_authorization: bool = False,
        issued_at: datetime | None = None,
    ) -> AuthorizationDecision:
        reason = PromotionGate._failure_reason(target, evidence, explicit_live_authorization)
        approved = reason is None
        if target == PromotionTarget.LIVE and approved:
            if not authorized_by or not authorized_by.strip():
                approved = False
                reason = "live promotion requires an explicit human authorization identity"

        return AuthorizationDecision(
            authorization_id=uuid4(),
            approved=approved,
            target=target,
            reason="approved" if approved else reason or "promotion rejected",
            strategy_fingerprint=evidence.strategy_fingerprint,
            dataset_fingerprint=evidence.dataset_fingerprint,
            authorized_by=authorized_by.strip() if authorized_by else None,
            issued_at=issued_at,
        )

    @staticmethod
    def _failure_reason(
        target: PromotionTarget,
        evidence: PromotionEvidence,
        explicit_live_authorization: bool,
    ) -> str | None:
        if target == PromotionTarget.PAPER:
            if not evidence.research_gate_passed:
                return "research gate has not passed"
            return None

        if target == PromotionTarget.TESTNET:
            if not evidence.research_gate_passed:
                return "research gate has not passed"
            if not evidence.paper_trading_passed:
                return "paper trading evidence has not passed"
            return None

        if target == PromotionTarget.LIVE:
            if not evidence.research_gate_passed:
                return "research gate has not passed"
            if not evidence.paper_trading_passed:
                return "paper trading evidence has not passed"
            if not evidence.testnet_passed:
                return "testnet evidence has not passed"
            if not evidence.risk_limits_fingerprint:
                return "risk limits evidence is required"
            if not explicit_live_authorization:
                return "explicit live authorization is required"
            return None

        return "unsupported promotion target"
