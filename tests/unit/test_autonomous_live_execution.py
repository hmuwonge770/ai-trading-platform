from decimal import Decimal
from uuid import uuid4

from packages.autonomy.authorization_consumption import LiveExecutionAuthorization
from packages.autonomy.control import AutonomousControl, AutonomousMode
from packages.autonomy.decision import Decision, DecisionAction
from packages.autonomy.live_execution import (
    AutonomousLiveExecutionBoundary,
    LiveExecutionStatus,
)
from packages.autonomy.risk import AutonomousRiskResult
from packages.trading.paper import OrderIntent


class RecordingSubmitter:
    def __init__(self) -> None:
        self.orders: list[OrderIntent] = []

    def submit(self, order: OrderIntent) -> object:
        self.orders.append(order)
        return {"exchange_order_id": "test-1"}


def make_fixture() -> tuple[LiveExecutionAuthorization, AutonomousRiskResult, AutonomousControl]:
    strategy_version_id = uuid4()
    decision = Decision(
        DecisionAction.BUY,
        "BTCUSDT",
        Decimal("0.80"),
        "test decision",
        1,
    )
    order = OrderIntent(
        intent_id=uuid4(),
        signal_id=uuid4(),
        strategy_version_id=str(strategy_version_id),
        symbol="BTCUSDT",
        timeframe="1m",
        side="BUY",
        quantity=Decimal("0.01"),
        reference_price=Decimal("100"),
        client_order_id="auto-test-1",
        reason="test",
    )
    risk = AutonomousRiskResult(True, "approved", "approved", decision, order, None)
    authorization = LiveExecutionAuthorization(
        authorization_hash="a" * 64,
        promotion_id=uuid4(),
        strategy_version_id=strategy_version_id,
        strategy_fingerprint="b" * 64,
        environment=AutonomousMode.LIVE,
        risk_policy_fingerprint="c" * 64,
        evidence_snapshot_hash="d" * 64,
        expires_at=None,
    )
    control = AutonomousControl(
        mode=AutonomousMode.LIVE,
        state="RUNNING",
        trading_enabled=True,
        kill_switch_enabled=False,
        circuit_breaker_open=False,
    )
    return authorization, risk, control


def test_submits_only_after_authorization_risk_and_control_checks() -> None:
    authorization, risk, control = make_fixture()
    submitter = RecordingSubmitter()

    report = AutonomousLiveExecutionBoundary(submitter).submit(
        authorization=authorization,
        risk_result=risk,
        control=control,
    )

    assert report.status is LiveExecutionStatus.SUBMITTED
    assert submitter.orders == [risk.order]


def test_non_live_control_is_blocked() -> None:
    authorization, risk, control = make_fixture()
    submitter = RecordingSubmitter()
    paper_control = control.with_mode(AutonomousMode.PAPER)

    report = AutonomousLiveExecutionBoundary(submitter).submit(
        authorization=authorization,
        risk_result=risk,
        control=paper_control,
    )

    assert report.status is LiveExecutionStatus.BLOCKED
    assert "control_mode_not_live" in report.reasons
    assert not submitter.orders


def test_unapproved_risk_is_blocked() -> None:
    authorization, risk, control = make_fixture()
    submitter = RecordingSubmitter()
    rejected = AutonomousRiskResult(False, "rejected", "risk rejected", risk.decision, risk.order, None)

    report = AutonomousLiveExecutionBoundary(submitter).submit(
        authorization=authorization,
        risk_result=rejected,
        control=control,
    )

    assert report.status is LiveExecutionStatus.BLOCKED
    assert "risk_not_approved" in report.reasons
    assert not submitter.orders


def test_strategy_version_mismatch_is_blocked() -> None:
    authorization, risk, control = make_fixture()
    submitter = RecordingSubmitter()
    mismatched = OrderIntent(
        intent_id=risk.order.intent_id,
        signal_id=risk.order.signal_id,
        strategy_version_id=str(uuid4()),
        symbol=risk.order.symbol,
        timeframe=risk.order.timeframe,
        side=risk.order.side,
        quantity=risk.order.quantity,
        reference_price=risk.order.reference_price,
        client_order_id=risk.order.client_order_id,
        reason=risk.order.reason,
    )
    risk = AutonomousRiskResult(True, "approved", "approved", risk.decision, mismatched, None)

    report = AutonomousLiveExecutionBoundary(submitter).submit(
        authorization=authorization,
        risk_result=risk,
        control=control,
    )

    assert report.status is LiveExecutionStatus.BLOCKED
    assert "strategy_version_mismatch" in report.reasons
    assert not submitter.orders


def test_duplicate_client_order_id_is_not_submitted_twice() -> None:
    authorization, risk, control = make_fixture()
    submitter = RecordingSubmitter()
    boundary = AutonomousLiveExecutionBoundary(submitter)

    first = boundary.submit(authorization=authorization, risk_result=risk, control=control)
    second = boundary.submit(authorization=authorization, risk_result=risk, control=control)

    assert first.status is LiveExecutionStatus.SUBMITTED
    assert second.status is LiveExecutionStatus.DUPLICATE
    assert len(submitter.orders) == 1


def test_submitter_failure_fails_closed() -> None:
    authorization, risk, control = make_fixture()

    class FailingSubmitter:
        def submit(self, order: OrderIntent) -> object:
            raise RuntimeError("exchange unavailable")

    report = AutonomousLiveExecutionBoundary(FailingSubmitter()).submit(
        authorization=authorization,
        risk_result=risk,
        control=control,
    )

    assert report.status is LiveExecutionStatus.BLOCKED
    assert report.reasons == ("live_submitter_failed:RuntimeError",)
