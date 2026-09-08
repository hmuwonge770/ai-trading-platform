"""Immutable governance contract for production-soak evidence.

AR is an evidence/readiness control-plane layer. It never activates live
execution, changes runtime state, widens risk or capital limits, or submits
exchange orders.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import StrEnum
import hashlib
import math
from uuid import UUID


class ProductionSoakAction(StrEnum):
    COMPLETE = "complete"
    HOLD = "hold"
    ABORT = "abort"


@dataclass(frozen=True, slots=True)
class ProductionSoakPolicy:
    """Externally approved boundaries for evaluating soak evidence."""

    minimum_duration_seconds: int = 86_400
    minimum_samples: int = 1_000
    maximum_evidence_age_seconds: int = 3_600
    max_error_rate_percent: Decimal = Decimal("1")
    max_reconciliation_failures: int = 0
    max_drawdown_percent: Decimal = Decimal("2")
    max_slippage_percent: Decimal = Decimal("1")
    max_missing_intervals: int = 0

    def __post_init__(self) -> None:
        if self.minimum_duration_seconds < 0:
            raise ValueError("minimum_duration_seconds cannot be negative")
        if self.minimum_samples < 0:
            raise ValueError("minimum_samples cannot be negative")
        if self.maximum_evidence_age_seconds < 0:
            raise ValueError("maximum_evidence_age_seconds cannot be negative")
        if self.max_reconciliation_failures < 0 or self.max_missing_intervals < 0:
            raise ValueError("failure counts cannot be negative")
        for name in ("max_error_rate_percent", "max_drawdown_percent", "max_slippage_percent"):
            value = _decimal(getattr(self, name), name)
            if value < 0:
                raise ValueError(f"{name} cannot be negative")
            object.__setattr__(self, name, value)


@dataclass(frozen=True, slots=True)
class ProductionSoakEvidence:
    strategy_version_id: UUID
    canary_run_id: UUID
    cohort_percent: Decimal
    started_at: datetime
    ended_at: datetime
    collected_at: datetime
    samples: int
    observed_error_rate_percent: Decimal
    reconciliation_failures: int
    observed_drawdown_percent: Decimal
    observed_slippage_percent: Decimal
    missing_intervals: int
    evidence_digest: str

    def __post_init__(self) -> None:
        for name in ("started_at", "ended_at", "collected_at"):
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must be timezone-aware")
        for name in ("cohort_percent", "observed_error_rate_percent", "observed_drawdown_percent", "observed_slippage_percent"):
            value = _decimal(getattr(self, name), name)
            if value < 0:
                raise ValueError(f"{name} cannot be negative")
            object.__setattr__(self, name, value)
        for name in ("samples", "reconciliation_failures", "missing_intervals"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} cannot be negative")
        if self.ended_at < self.started_at:
            raise ValueError("ended_at cannot precede started_at")
        if self.collected_at < self.ended_at:
            raise ValueError("collected_at cannot precede ended_at")
        if len(self.evidence_digest) != 64 or any(c not in "0123456789abcdef" for c in self.evidence_digest):
            raise ValueError("evidence_digest must be a lowercase SHA-256 hex digest")

    def canonical_payload(self) -> str:
        """Return the deterministic evidence representation used for hashing."""
        return "|".join((
            str(self.strategy_version_id), str(self.canary_run_id), str(self.cohort_percent),
            self.started_at.astimezone(timezone.utc).isoformat(),
            self.ended_at.astimezone(timezone.utc).isoformat(),
            self.collected_at.astimezone(timezone.utc).isoformat(),
            str(self.samples), str(self.observed_error_rate_percent),
            str(self.reconciliation_failures), str(self.observed_drawdown_percent),
            str(self.observed_slippage_percent), str(self.missing_intervals),
        ))

    def digest_matches(self) -> bool:
        return hashlib.sha256(self.canonical_payload().encode("utf-8")).hexdigest() == self.evidence_digest


def _decimal(value: Decimal | int | float | str, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{field} must be a finite decimal") from None
    if not result.is_finite() or (isinstance(value, float) and not math.isfinite(value)):
        raise ValueError(f"{field} must be a finite decimal")
    return result


def build_evidence_digest(evidence: ProductionSoakEvidence) -> str:
    """Compute the canonical SHA-256 digest without trusting the supplied digest."""
    return hashlib.sha256(evidence.canonical_payload().encode("utf-8")).hexdigest()
