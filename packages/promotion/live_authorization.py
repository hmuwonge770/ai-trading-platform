from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from .domain import Approval, ApprovalDecision, ApprovalRole, AuthorizationSnapshot
from .readiness import ProductionReadinessReport


REQUIRED_ROLES = frozenset({ApprovalRole.RISK_MANAGER, ApprovalRole.ADMIN})


@dataclass(frozen=True, slots=True)
class LiveAuthorization:
    """Immutable authorization produced only from a frozen, fully approved snapshot."""

    promotion_id: str
    strategy_version_id: str
    strategy_fingerprint: str
    risk_policy_fingerprint: str
    capital: Decimal
    max_position_value: Decimal
    max_daily_loss: Decimal
    max_orders_per_day: int
    evidence_snapshot_hash: str
    authorization_hash: str
    approved_by: tuple[str, ...]


class TwoPersonLiveAuthorization:
    """Stage 31 gate: two independent authorized humans approve one exact snapshot."""

    @staticmethod
    def authorize(
        *,
        readiness: ProductionReadinessReport,
        snapshot: AuthorizationSnapshot,
        approvals: Iterable[Approval],
        requested_by: str,
    ) -> LiveAuthorization:
        if not readiness.live_eligible:
            raise PermissionError("Production readiness is not LIVE_ELIGIBLE")
        if snapshot.strategy_version_id.__str__() != readiness.strategy_version_id:
            raise ValueError("Readiness strategy version does not match authorization")
        if snapshot.strategy_fingerprint != readiness.strategy_fingerprint:
            raise ValueError("Readiness strategy fingerprint does not match authorization")
        if not requested_by.strip():
            raise ValueError("requested_by is required")

        approvals = tuple(approvals)
        if len(approvals) < 2:
            raise PermissionError("Two independent approvals are required")

        approved = tuple(a for a in approvals if a.decision == ApprovalDecision.APPROVE)
        approver_ids = {a.approver_id for a in approved}
        roles = {a.role for a in approved}
        if len(approver_ids) != len(approved):
            raise PermissionError("Approvers must be distinct")
        if requested_by in approver_ids:
            raise PermissionError("Requester cannot approve the same authorization")
        if not REQUIRED_ROLES.issubset(roles):
            raise PermissionError("Risk Manager and Admin approvals are required")
        if any(a.fingerprint != snapshot.strategy_fingerprint for a in approved):
            raise ValueError("Approval strategy fingerprint does not match snapshot")
        if any(a.capital_limit != snapshot.capital_allocation.max_capital for a in approved):
            raise ValueError("Approval capital limit does not match snapshot")

        return LiveAuthorization(
            promotion_id=str(snapshot.promotion_id),
            strategy_version_id=str(snapshot.strategy_version_id),
            strategy_fingerprint=snapshot.strategy_fingerprint,
            risk_policy_fingerprint=snapshot.risk_policy_fingerprint,
            capital=snapshot.capital_allocation.max_capital,
            max_position_value=snapshot.capital_allocation.max_position_value,
            max_daily_loss=snapshot.capital_allocation.max_daily_loss,
            max_orders_per_day=snapshot.capital_allocation.max_orders_per_day,
            evidence_snapshot_hash=snapshot.evidence_snapshot_hash,
            authorization_hash=snapshot.authorization_hash,
            approved_by=tuple(sorted(approver_ids)),
        )

    @staticmethod
    def is_unchanged(
        authorization: LiveAuthorization,
        *,
        snapshot: AuthorizationSnapshot,
        strategy_fingerprint: str,
        risk_policy_fingerprint: str,
        capital: Decimal,
    ) -> bool:
        """Return false when any material authorized value has changed."""
        return (
            authorization.authorization_hash == snapshot.authorization_hash
            and authorization.strategy_fingerprint == strategy_fingerprint
            and authorization.risk_policy_fingerprint == risk_policy_fingerprint
            and authorization.capital == capital
            and authorization.strategy_version_id == str(snapshot.strategy_version_id)
            and authorization.evidence_snapshot_hash == snapshot.evidence_snapshot_hash
        )
