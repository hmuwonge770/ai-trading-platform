"""Credential-isolated preflight for a future live exchange adapter.

This module validates adapter configuration without storing credentials or
submitting orders. It produces a readiness result that a runtime may use before
constructing a separately controlled exchange capability.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class LiveAdapterStatus(StrEnum):
    READY = "ready"
    BLOCKED = "blocked"


class LiveExchangeTransport(Protocol):
    """Minimal capability for a separately implemented live adapter."""

    def healthcheck(self) -> bool: ...


@dataclass(frozen=True, slots=True)
class LiveAdapterPreflightContext:
    endpoint: str
    credential_reference: str
    account_enabled: bool
    healthcheck_passed: bool


@dataclass(frozen=True, slots=True)
class LiveAdapterPolicy:
    production_endpoint: str = "https://api.binance.com"

    def __post_init__(self) -> None:
        if not self.production_endpoint.startswith("https://"):
            raise ValueError("production_endpoint must use HTTPS")


@dataclass(frozen=True, slots=True)
class LiveAdapterPreflightReport:
    status: LiveAdapterStatus
    endpoint: str
    reasons: tuple[str, ...]

    @property
    def ready(self) -> bool:
        return self.status is LiveAdapterStatus.READY


class AutonomousLiveAdapterPreflight:
    """Validate a live adapter boundary without creating exchange state."""

    def __init__(self, *, policy: LiveAdapterPolicy | None = None) -> None:
        self.policy = policy or LiveAdapterPolicy()

    def assess(self, context: LiveAdapterPreflightContext) -> LiveAdapterPreflightReport:
        reasons: list[str] = []
        endpoint = context.endpoint.rstrip("/")

        if endpoint != self.policy.production_endpoint.rstrip("/"):
            reasons.append("endpoint_not_approved")
        if "testnet" in endpoint.lower() or "sandbox" in endpoint.lower():
            reasons.append("test_environment_not_allowed")
        if not context.credential_reference.strip():
            reasons.append("credential_reference_missing")
        if not context.account_enabled:
            reasons.append("account_disabled")
        if not context.healthcheck_passed:
            reasons.append("adapter_healthcheck_failed")

        return LiveAdapterPreflightReport(
            LiveAdapterStatus.BLOCKED if reasons else LiveAdapterStatus.READY,
            endpoint,
            tuple(reasons),
        )
