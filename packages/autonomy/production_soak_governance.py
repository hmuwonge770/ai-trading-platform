"""Deterministic governance for evaluating bounded production-soak evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID

from .production_soak import ProductionSoakAction, ProductionSoakEvidence, ProductionSoakPolicy


class ProductionSoakDecision(StrEnum):
    COMPLETE = "complete"
    HOLD = "hold"
    ABORT = "abort"


@dataclass(frozen=True, slots=True)
class ProductionSoakReport:
    strategy_version_id: UUID
    canary_run_id: UUID
    action: ProductionSoakAction
    safe: bool
    evidence_valid: bool
    duration_seconds: int
    evidence_age_seconds: int
    reasons: tuple[str, ...] = ()

    @property
    def soak_complete(self) -> bool:
        return self.action is ProductionSoakAction.COMPLETE


class AutonomousProductionSoakGovernance:
    """Evaluate evidence only; never mutate the runtime or execution state."""

    def __init__(self, *, policy: ProductionSoakPolicy | None = None) -> None:
        self.policy = policy or ProductionSoakPolicy()

    def evaluate(
        self,
        evidence: ProductionSoakEvidence,
        *,
        expected_strategy_version_id: UUID,
        expected_canary_run_id: UUID,
        canary_completed: bool,
        promotion_approved: bool,
        risk_approved: bool,
        capital_approved: bool,
        runtime_ready: bool,
        kill_switch_clear: bool,
        now: datetime,
    ) -> ProductionSoakReport:
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("now must be timezone-aware")
        if evidence.strategy_version_id != expected_strategy_version_id:
            return self._abort(evidence, "strategy_identity_mismatch")
        if evidence.canary_run_id != expected_canary_run_id:
            return self._abort(evidence, "canary_run_identity_mismatch")

        current = now.astimezone(timezone.utc)
        ended = evidence.ended_at.astimezone(timezone.utc)
        duration = int((ended - evidence.started_at.astimezone(timezone.utc)).total_seconds())
        age = int((current - ended).total_seconds())
        reasons: list[str] = []

        if duration < 0 or age < 0:
            return self._abort(evidence, "invalid_evidence_time_window")
        if not evidence.digest_matches():
            return self._abort(evidence, "evidence_digest_mismatch")
        if age > self.policy.maximum_evidence_age_seconds:
            return self._abort(evidence, "evidence_stale")
        if not canary_completed:
            reasons.append("canary_not_completed")
        if not promotion_approved:
            reasons.append("promotion_governance_not_approved")
        if not risk_approved:
            reasons.append("risk_governance_not_approved")
        if not capital_approved:
            reasons.append("capital_governance_not_approved")
        if not runtime_ready:
            reasons.append("runtime_not_ready")
        if not kill_switch_clear:
            reasons.append("deployment_kill_switch_active")
        if duration < self.policy.minimum_duration_seconds:
            reasons.append("insufficient_soak_duration")
        if evidence.samples < self.policy.minimum_samples:
            reasons.append("insufficient_evidence_samples")
        if evidence.reconciliation_failures > self.policy.max_reconciliation_failures:
            reasons.append("reconciliation_failures_exceeded")
        if evidence.missing_intervals > self.policy.max_missing_intervals:
            reasons.append("missing_intervals_exceeded")
        if evidence.observed_error_rate_percent > self.policy.max_error_rate_percent:
            reasons.append("error_rate_exceeded")
        if evidence.observed_drawdown_percent > self.policy.max_drawdown_percent:
            reasons.append("drawdown_exceeded")
        if evidence.observed_slippage_percent > self.policy.max_slippage_percent:
            reasons.append("slippage_exceeded")

        critical = {
            "canary_not_completed",
            "promotion_governance_not_approved", "risk_governance_not_approved",
            "capital_governance_not_approved", "runtime_not_ready",
            "deployment_kill_switch_active", "reconciliation_failures_exceeded",
            "missing_intervals_exceeded", "error_rate_exceeded", "drawdown_exceeded",
            "slippage_exceeded",
        }
        action = ProductionSoakAction.ABORT if any(r in critical for r in reasons) else (
            ProductionSoakAction.HOLD if reasons else ProductionSoakAction.COMPLETE
        )
        return ProductionSoakReport(
            strategy_version_id=evidence.strategy_version_id,
            canary_run_id=evidence.canary_run_id,
            action=action,
            safe=action is not ProductionSoakAction.ABORT,
            evidence_valid=True,
            duration_seconds=duration,
            evidence_age_seconds=age,
            reasons=tuple(dict.fromkeys(reasons)),
        )

    def _abort(self, evidence: ProductionSoakEvidence, reason: str) -> ProductionSoakReport:
        return ProductionSoakReport(
            strategy_version_id=evidence.strategy_version_id,
            canary_run_id=evidence.canary_run_id,
            action=ProductionSoakAction.ABORT,
            safe=False,
            evidence_valid=False,
            duration_seconds=max(0, int((evidence.ended_at - evidence.started_at).total_seconds())),
            evidence_age_seconds=0,
            reasons=(reason,),
        )
