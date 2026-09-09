from packages.autonomy.end_to_end_failure_testing import FailureInjection, FailureResponse, FailureType
from packages.autonomy.end_to_end_failure_testing_integration import AutonomousEndToEndFailureGovernance, FailureGovernanceContext


def test_identity_mismatch_halts():
    injection = FailureInjection(FailureType.EXCHANGE_DISCONNECT, "s1", "v1")
    result = AutonomousEndToEndFailureGovernance().assess(FailureGovernanceContext("s2", "v1", injection))
    assert result.response is FailureResponse.HALT
    assert not result.safe


def test_reconciliation_fault_is_bounded():
    injection = FailureInjection(FailureType.ACCOUNTING_MISMATCH, "s1", "v1")
    result = AutonomousEndToEndFailureGovernance().assess(FailureGovernanceContext("s1", "v1", injection))
    assert result.response is FailureResponse.RECONCILE
    assert result.safe
