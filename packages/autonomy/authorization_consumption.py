"""Read-only final-boundary validation for consuming live authorization.

This module converts a freshly validated authorization snapshot plus its
persisted authorization record into an immutable execution authorization.
It never approves, activates, renews, or mutates authorization and performs
no exchange operations.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from packages.promotion.domain import AuthorizationRecord, AuthorizationSnapshot, LIVE_STAGES

from .authorization_freshness import (
    AutonomousAuthorizationFreshnessGuard,
    AuthorizationFreshnessContext,
    AuthorizationFreshnessStatus,
)


class AuthorizationConsumptionStatus(StrEnum):
    AUTHORIZED = "authorized"
    BLOCKED = "blocked"
    EXPIRED = "expired"


@dataclass(frozen=True, slots=True)
class LiveExecutionAuthorization:
    """Immutable authorization evidence handed to a future live executor."""

    authorization_hash: str
    promotion_id: object
    strategy_version_id: object
    strategy_fingerprint: str
    environment: object
    risk_policy_fingerprint: str
    evidence_snapshot_hash: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class AuthorizationConsumptionReport:
    status: AuthorizationConsumptionStatus
    authorization: LiveExecutionAuthorization | None
    reasons: tuple[str, ...]

    @property
    def authorized(self) -> bool:
        return self.status is AuthorizationConsumptionStatus.AUTHORIZED


class AutonomousLiveAuthorizationConsumer:
    """Fail-closed final consumer for an already human-authorized snapshot."""

    def __init__(self, *, freshness_guard: AutonomousAuthorizationFreshnessGuard | None = None) -> None:
        self._freshness_guard = freshness_guard or AutonomousAuthorizationFreshnessGuard()

    def assess(
        self,
        snapshot: AuthorizationSnapshot,
        record: AuthorizationRecord,
        context: AuthorizationFreshnessContext,
    ) -> AuthorizationConsumptionReport:
        freshness = self._freshness_guard.assess(snapshot, context)
        reasons = list(freshness.reasons)

        if record.authorization_hash != snapshot.authorization_hash:
            reasons.append("authorization_hash_mismatch")
        if record.promotion_status is not context.promotion_status:
            reasons.append("persisted_promotion_status_mismatch")
        if record.strategy_version_id != snapshot.strategy_version_id:
            reasons.append("persisted_strategy_version_mismatch")
        if record.strategy_fingerprint != snapshot.strategy_fingerprint:
            reasons.append("persisted_strategy_fingerprint_mismatch")
        if record.environment is not snapshot.environment:
            reasons.append("persisted_environment_mismatch")
        if record.risk_policy_fingerprint != snapshot.risk_policy_fingerprint:
            reasons.append("persisted_risk_policy_fingerprint_mismatch")
        if record.expires_at != snapshot.expires_at:
            reasons.append("persisted_expiry_mismatch")
        if snapshot.environment not in LIVE_STAGES:
            reasons.append("authorization_environment_not_live")

        if freshness.status is AuthorizationFreshnessStatus.EXPIRED:
            return AuthorizationConsumptionReport(
                AuthorizationConsumptionStatus.EXPIRED, None, tuple(dict.fromkeys(reasons))
            )
        if not freshness.valid or reasons:
            return AuthorizationConsumptionReport(
                AuthorizationConsumptionStatus.BLOCKED, None, tuple(dict.fromkeys(reasons))
            )

        authorization = LiveExecutionAuthorization(
            authorization_hash=snapshot.authorization_hash,
            promotion_id=snapshot.promotion_id,
            strategy_version_id=snapshot.strategy_version_id,
            strategy_fingerprint=snapshot.strategy_fingerprint,
            environment=snapshot.environment,
            risk_policy_fingerprint=snapshot.risk_policy_fingerprint,
            evidence_snapshot_hash=snapshot.evidence_snapshot_hash,
            expires_at=snapshot.expires_at,
        )
        return AuthorizationConsumptionReport(
            AuthorizationConsumptionStatus.AUTHORIZED, authorization, ()
        )
