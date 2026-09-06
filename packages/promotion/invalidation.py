from __future__ import annotations

from dataclasses import dataclass

from .domain import AuthorizationSnapshot


@dataclass(frozen=True)
class AuthorizationBinding:
    strategy_fingerprint: str
    risk_policy_fingerprint: str
    authorization_hash: str


class AuthorizationValidator:
    """Detects changes that must invalidate a live authorization."""

    @staticmethod
    def binding(snapshot: AuthorizationSnapshot) -> AuthorizationBinding:
        return AuthorizationBinding(
            strategy_fingerprint=snapshot.strategy_fingerprint,
            risk_policy_fingerprint=snapshot.risk_policy_fingerprint,
            authorization_hash=snapshot.authorization_hash,
        )

    @staticmethod
    def is_current(snapshot: AuthorizationSnapshot, binding: AuthorizationBinding) -> bool:
        return (
            snapshot.strategy_fingerprint == binding.strategy_fingerprint
            and snapshot.risk_policy_fingerprint == binding.risk_policy_fingerprint
            and snapshot.authorization_hash == binding.authorization_hash
        )
