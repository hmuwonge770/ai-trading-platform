from __future__ import annotations

import pytest

from packages.promotion.readiness import (
    ProductionReadinessGate,
    ReadinessEvidence,
    ReadinessGate,
)


FINGERPRINT = "a" * 64
ALL_EVIDENCE = tuple(
    ReadinessEvidence(gate=gate, passed=True, evidence_id=f"evidence-{gate.value}")
    for gate in ReadinessGate
)


def test_all_required_gates_pass_makes_strategy_live_eligible() -> None:
    report = ProductionReadinessGate().evaluate(
        strategy_version_id="strategy-v1",
        strategy_fingerprint=FINGERPRINT,
        evidence=ALL_EVIDENCE,
    )

    assert report.live_eligible is True
    assert report.failed_gates == ()
    assert report.missing_gates == ()


def test_missing_gate_fails_closed() -> None:
    evidence = tuple(item for item in ALL_EVIDENCE if item.gate != ReadinessGate.BACKUP_RESTORE)

    report = ProductionReadinessGate().evaluate(
        strategy_version_id="strategy-v1",
        strategy_fingerprint=FINGERPRINT,
        evidence=evidence,
    )

    assert report.live_eligible is False
    assert report.missing_gates == (ReadinessGate.BACKUP_RESTORE,)


def test_failed_gate_blocks_eligibility() -> None:
    evidence = tuple(
        ReadinessEvidence(item.gate, item.gate != ReadinessGate.SECURITY, item.evidence_id)
        for item in ALL_EVIDENCE
    )

    report = ProductionReadinessGate().evaluate(
        strategy_version_id="strategy-v1",
        strategy_fingerprint=FINGERPRINT,
        evidence=evidence,
    )

    assert report.live_eligible is False
    assert report.failed_gates == (ReadinessGate.SECURITY,)


def test_duplicate_gate_is_rejected() -> None:
    evidence = ALL_EVIDENCE + (ALL_EVIDENCE[0],)

    with pytest.raises(ValueError, match="duplicate readiness gate"):
        ProductionReadinessGate().evaluate(
            strategy_version_id="strategy-v1",
            strategy_fingerprint=FINGERPRINT,
            evidence=evidence,
        )


def test_invalid_strategy_fingerprint_is_rejected() -> None:
    with pytest.raises(ValueError, match="SHA-256"):
        ProductionReadinessGate().evaluate(
            strategy_version_id="strategy-v1",
            strategy_fingerprint="not-a-fingerprint",
            evidence=ALL_EVIDENCE,
        )


def test_empty_evidence_id_is_rejected() -> None:
    evidence = ALL_EVIDENCE[:-1] + (
        ReadinessEvidence(ReadinessGate.KUBERNETES, True, "   "),
    )

    with pytest.raises(ValueError, match="evidence_id"):
        ProductionReadinessGate().evaluate(
            strategy_version_id="strategy-v1",
            strategy_fingerprint=FINGERPRINT,
            evidence=evidence,
        )
