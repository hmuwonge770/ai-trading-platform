"""Restart-safe decision ledger contract for AZ production operation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .production_operation import ProductionOperationAssessment


@dataclass(frozen=True, slots=True)
class ProductionOperationDecision:
    strategy_version_id: str
    strategy_fingerprint: str
    revision: int
    assessment: ProductionOperationAssessment
    digest: str

    @classmethod
    def create(
        cls,
        *,
        strategy_version_id: str,
        strategy_fingerprint: str,
        revision: int,
        assessment: ProductionOperationAssessment,
    ) -> ProductionOperationDecision:
        if not strategy_version_id or not strategy_fingerprint:
            raise ValueError("strategy identity is required")
        if revision < 0:
            raise ValueError("revision must be non-negative")
        payload = {
            "strategy_version_id": strategy_version_id,
            "strategy_fingerprint": strategy_fingerprint,
            "revision": revision,
            "action": assessment.action.value,
            "reasons": assessment.reasons,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return cls(strategy_version_id, strategy_fingerprint, revision, assessment, digest)


class InMemoryProductionOperationLedger:
    """Deterministic reference ledger; production storage must provide equivalent semantics."""

    def __init__(self) -> None:
        self._records: dict[tuple[str, str, int], ProductionOperationDecision] = {}

    def record(self, decision: ProductionOperationDecision) -> ProductionOperationDecision:
        key = (
            decision.strategy_version_id,
            decision.strategy_fingerprint,
            decision.revision,
        )
        existing = self._records.get(key)
        if existing is not None and existing.digest != decision.digest:
            raise ValueError("conflicting production operation decision")
        self._records[key] = decision
        return self._records[key]

    def get(
        self,
        *,
        strategy_version_id: str,
        strategy_fingerprint: str,
        revision: int,
    ) -> ProductionOperationDecision | None:
        return self._records.get((strategy_version_id, strategy_fingerprint, revision))
