"""Read-only validation of live authorization freshness and integrity.

This module verifies that an existing authorization snapshot is still valid for
execution. It never renews, mutates, approves, or activates authorization.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID

from packages.promotion.domain import LIVE_STAGES, AuthorizationSnapshot, PromotionStage, PromotionStatus


class AuthorizationFreshnessStatus(StrEnum):
    VALID = "valid"
    EXPIRED = "expired"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class AuthorizationFreshnessContext:
    """Current immutable execution context used to validate an authorization."""

    promotion_id: UUID
    promotion_status: PromotionStatus
    strategy_version_id: UUID
    strategy_fingerprint: str
    environment: PromotionStage
    risk_policy_fingerprint: str
    evidence_snapshot_hash: str
    now: datetime


@dataclass(frozen=True, slots=True)
class AuthorizationFreshnessReport:
    status: AuthorizationFreshnessStatus
    promotion_id: UUID
    authorization_hash: str
    reasons: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return self.status is AuthorizationFreshnessStatus.VALID


class AutonomousAuthorizationFreshnessGuard:
    """Fail-closed freshness/integrity guard for a live authorization snapshot."""

    def assess(
        self,
        snapshot: AuthorizationSnapshot,
        context: AuthorizationFreshnessContext,
    ) -> AuthorizationFreshnessReport:
        reasons: list[str] = []
        snapshot_hash = snapshot.authorization_hash

        if context.now.tzinfo is None:
            raise ValueError("context.now must be timezone-aware")
        now = context.now.astimezone(timezone.utc)
        expires_at = snapshot.expires_at
        if expires_at.tzinfo is None:
            raise ValueError("authorization expiry must be timezone-aware")
        expires_at = expires_at.astimezone(timezone.utc)

        if context.promotion_id != snapshot.promotion_id:
            reasons.append("promotion_id_mismatch")
        if context.promotion_status is not PromotionStatus.APPROVED:
            reasons.append("promotion_not_approved")
        if snapshot.environment not in LIVE_STAGES:
            reasons.append("authorization_environment_not_live")
        if context.environment is not snapshot.environment:
            reasons.append("environment_mismatch")
        if context.strategy_version_id != snapshot.strategy_version_id:
            reasons.append("strategy_version_mismatch")
        if context.strategy_fingerprint != snapshot.strategy_fingerprint:
            reasons.append("strategy_fingerprint_mismatch")
        if context.risk_policy_fingerprint != snapshot.risk_policy_fingerprint:
            reasons.append("risk_policy_fingerprint_mismatch")
        if context.evidence_snapshot_hash != snapshot.evidence_snapshot_hash:
            reasons.append("evidence_snapshot_hash_mismatch")
        if not snapshot.authorization_hash or len(snapshot.authorization_hash) != 64:
            reasons.append("invalid_authorization_hash")
        if now >= expires_at:
            return AuthorizationFreshnessReport(
                AuthorizationFreshnessStatus.EXPIRED,
                snapshot.promotion_id,
                snapshot_hash,
                tuple(reasons) + ("authorization_expired",),
            )

        status = AuthorizationFreshnessStatus.BLOCKED if reasons else AuthorizationFreshnessStatus.VALID
        return AuthorizationFreshnessReport(status, snapshot.promotion_id, snapshot_hash, tuple(reasons))
