"""Append-only audit events for autonomous live execution orchestration.

The audit layer records control decisions and execution outcomes without
holding credentials, exchange clients, or mutable trading state.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class ExecutionAuditStatus(StrEnum):
    SUBMITTED = "submitted"
    BLOCKED = "blocked"
    DUPLICATE = "duplicate"
    DRY_RUN = "dry_run"
    PREFLIGHT = "preflight"


@dataclass(frozen=True, slots=True)
class ExecutionAuditEvent:
    """Immutable, secret-free record of one orchestration outcome."""

    event_id: str
    status: ExecutionAuditStatus
    runtime_mode: str
    client_order_id: str
    strategy_version_id: str
    strategy_fingerprint: str
    authorization_hash: str
    risk_approved: bool
    occurred_at: int
    reasons: tuple[str, ...] = ()
    exchange_order_id: str | None = None

    @classmethod
    def create(
        cls,
        *,
        status: ExecutionAuditStatus,
        runtime_mode: str,
        client_order_id: str,
        strategy_version_id: str,
        strategy_fingerprint: str,
        authorization_hash: str,
        risk_approved: bool,
        occurred_at: int,
        reasons: tuple[str, ...] = (),
        exchange_order_id: str | None = None,
    ) -> "ExecutionAuditEvent":
        if occurred_at <= 0:
            raise ValueError("occurred_at must be positive")
        if not strategy_version_id.strip():
            raise ValueError("strategy_version_id must not be empty")
        if not strategy_fingerprint.strip() or not authorization_hash.strip():
            raise ValueError("strategy fingerprint and authorization hash are required")
        payload = {
            "status": status.value,
            "runtime_mode": runtime_mode,
            "client_order_id": client_order_id,
            "strategy_version_id": strategy_version_id,
            "strategy_fingerprint": strategy_fingerprint,
            "authorization_hash": authorization_hash,
            "risk_approved": risk_approved,
            "occurred_at": occurred_at,
            "reasons": list(reasons),
            "exchange_order_id": exchange_order_id,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        event_id = hashlib.sha256(encoded).hexdigest()
        return cls(event_id, status, runtime_mode, client_order_id, strategy_version_id,
                   strategy_fingerprint, authorization_hash, risk_approved, occurred_at,
                   tuple(reasons), exchange_order_id)


class ExecutionAuditSink(Protocol):
    """Append-only capability supplied by the application audit store."""

    def append(self, event: ExecutionAuditEvent) -> None: ...
