from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ReadinessGate(StrEnum):
    RESEARCH = "research"
    PAPER = "paper"
    TESTNET = "testnet"
    SECURITY = "security"
    FAILURE = "failure"
    RECONCILIATION = "reconciliation"
    BACKUP_RESTORE = "backup_restore"
    OBSERVABILITY = "observability"
    SOAK = "soak"
    KUBERNETES = "kubernetes"


@dataclass(frozen=True, slots=True)
class ReadinessEvidence:
    gate: ReadinessGate
    passed: bool
    evidence_id: str

    def validate(self) -> None:
        if not self.evidence_id.strip():
            raise ValueError("readiness evidence_id must not be empty")


@dataclass(frozen=True, slots=True)
class ProductionReadinessReport:
    """Fail-closed readiness result; never grants live authorization."""

    strategy_version_id: str
    strategy_fingerprint: str
    evidence: tuple[ReadinessEvidence, ...]

    @property
    def failed_gates(self) -> tuple[ReadinessGate, ...]:
        return tuple(item.gate for item in self.evidence if not item.passed)

    @property
    def missing_gates(self) -> tuple[ReadinessGate, ...]:
        present = {item.gate for item in self.evidence}
        return tuple(gate for gate in ReadinessGate if gate not in present)

    @property
    def live_eligible(self) -> bool:
        return not self.missing_gates and not self.failed_gates

    def validate(self) -> None:
        if not self.strategy_version_id.strip():
            raise ValueError("strategy_version_id must not be empty")
        if len(self.strategy_fingerprint) != 64:
            raise ValueError("strategy_fingerprint must be a SHA-256 hex digest")
        try:
            int(self.strategy_fingerprint, 16)
        except ValueError as exc:
            raise ValueError("strategy_fingerprint must be hexadecimal") from exc
        seen: set[ReadinessGate] = set()
        for item in self.evidence:
            item.validate()
            if item.gate in seen:
                raise ValueError(f"duplicate readiness gate: {item.gate.value}")
            seen.add(item.gate)


class ProductionReadinessGate:
    """Evaluate deterministic evidence without granting live authorization."""

    REQUIRED_GATES = tuple(ReadinessGate)

    def evaluate(self, *, strategy_version_id: str, strategy_fingerprint: str,
                 evidence: tuple[ReadinessEvidence, ...]) -> ProductionReadinessReport:
        report = ProductionReadinessReport(strategy_version_id, strategy_fingerprint, evidence)
        report.validate()
        return report
