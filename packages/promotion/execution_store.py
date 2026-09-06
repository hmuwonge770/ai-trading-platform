from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from packages.promotion.domain import AuthorizationRecord, PromotionStage, PromotionStatus


@dataclass(frozen=True, slots=True)
class PromotionAuthorizationStore:
    """Read-only PostgreSQL adapter used by the final execution gate."""

    db: Session

    def load(self, authorization_hash: str) -> AuthorizationRecord | None:
        row = self.db.execute(
            text("""
                SELECT a.authorization_hash, p.status, a.strategy_version_id,
                       a.strategy_fingerprint, a.environment,
                       a.risk_policy_fingerprint, a.expires_at
                FROM authorization_snapshots a
                JOIN strategy_promotions p ON p.id = a.promotion_id
                WHERE a.authorization_hash = :authorization_hash
                LIMIT 1
            """),
            {"authorization_hash": authorization_hash},
        ).mappings().first()
        if row is None:
            return None
        return AuthorizationRecord(
            authorization_hash=str(row["authorization_hash"]),
            promotion_status=PromotionStatus(row["status"]),
            strategy_version_id=UUID(str(row["strategy_version_id"])),
            strategy_fingerprint=str(row["strategy_fingerprint"]),
            environment=PromotionStage(row["environment"]),
            risk_policy_fingerprint=str(row["risk_policy_fingerprint"]),
            expires_at=row["expires_at"],
        )
