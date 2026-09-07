"""Controlled orchestration for the future autonomous live execution path."""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum

from .authorization_consumption import AuthorizationConsumptionReport, LiveExecutionAuthorization
from .control import AutonomousControl
from .live_adapter import LiveAdapterPreflightContext
from .live_execution import AutonomousLiveExecutionBoundary, LiveExecutionReport, LiveExecutionStatus
from .live_runtime import AutonomousLiveRuntimeGuard, LiveRuntimeConfig, LiveRuntimeMode, LiveRuntimeReport
from .observability import ExecutionAuditEvent, ExecutionAuditSink, ExecutionAuditStatus
from .risk import AutonomousRiskResult


class LiveOrchestrationStatus(StrEnum):
    SUBMITTED = "submitted"
    BLOCKED = "blocked"
    DRY_RUN = "dry_run"
    PREFLIGHT = "preflight"


@dataclass(frozen=True, slots=True)
class LiveOrchestrationReport:
    status: LiveOrchestrationStatus
    runtime: LiveRuntimeReport
    execution: LiveExecutionReport | None
    reasons: tuple[str, ...]

    @property
    def submitted(self) -> bool:
        return self.status is LiveOrchestrationStatus.SUBMITTED


class AutonomousLiveRuntimeOrchestrator:
    """Compose runtime controls with the existing live execution boundary."""

    def __init__(
        self,
        *,
        runtime_guard: AutonomousLiveRuntimeGuard,
        execution_boundary: AutonomousLiveExecutionBoundary,
        audit_sink: ExecutionAuditSink | None = None,
        clock: callable | None = None,
    ) -> None:
        self._runtime_guard = runtime_guard
        self._execution_boundary = execution_boundary
        self._audit_sink = audit_sink
        self._clock = clock or (lambda: int(time.time()))

    def execute(
        self,
        *,
        config: LiveRuntimeConfig,
        control: AutonomousControl,
        authorization: AuthorizationConsumptionReport,
        authorization_snapshot: LiveExecutionAuthorization | None,
        risk_result: AutonomousRiskResult,
        adapter: LiveAdapterPreflightContext,
    ) -> LiveOrchestrationReport:
        runtime = self._runtime_guard.assess(config, control, authorization, adapter)
        if config.mode is LiveRuntimeMode.PREFLIGHT:
            report = LiveOrchestrationReport(LiveOrchestrationStatus.PREFLIGHT, runtime, None, runtime.reasons)
            self._audit(report, config, authorization_snapshot, risk_result)
            return report
        if config.mode is LiveRuntimeMode.DRY_RUN:
            report = LiveOrchestrationReport(LiveOrchestrationStatus.DRY_RUN, runtime, None, runtime.reasons)
            self._audit(report, config, authorization_snapshot, risk_result)
            return report
        if not runtime.submit_allowed:
            report = LiveOrchestrationReport(LiveOrchestrationStatus.BLOCKED, runtime, None, runtime.reasons)
            self._audit(report, config, authorization_snapshot, risk_result)
            return report
        if authorization_snapshot is None:
            report = LiveOrchestrationReport(
                LiveOrchestrationStatus.BLOCKED, runtime, None, ("live_authorization_snapshot_missing",)
            )
            self._audit(report, config, authorization_snapshot, risk_result)
            return report

        execution = self._execution_boundary.submit(
            authorization=authorization_snapshot,
            risk_result=risk_result,
            control=control,
        )
        status = (
            LiveOrchestrationStatus.SUBMITTED
            if execution.status is LiveExecutionStatus.SUBMITTED
            else LiveOrchestrationStatus.BLOCKED
        )
        report = LiveOrchestrationReport(status, runtime, execution, execution.reasons)
        self._audit(report, config, authorization_snapshot, risk_result)
        return report

    def _audit(
        self,
        report: LiveOrchestrationReport,
        config: LiveRuntimeConfig,
        authorization: LiveExecutionAuthorization | None,
        risk_result: AutonomousRiskResult,
    ) -> None:
        if self._audit_sink is None:
            return
        order = risk_result.order
        strategy_version_id = order.strategy_version_id if order is not None else (
            str(authorization.strategy_version_id) if authorization is not None else "runtime"
        )
        fingerprint = authorization.strategy_fingerprint if authorization is not None else "runtime"
        auth_hash = authorization.authorization_hash if authorization is not None else "runtime"
        status = {
            LiveOrchestrationStatus.SUBMITTED: ExecutionAuditStatus.SUBMITTED,
            LiveOrchestrationStatus.BLOCKED: ExecutionAuditStatus.BLOCKED,
            LiveOrchestrationStatus.DRY_RUN: ExecutionAuditStatus.DRY_RUN,
            LiveOrchestrationStatus.PREFLIGHT: ExecutionAuditStatus.PREFLIGHT,
        }[report.status]
        exchange_order_id = None
        if report.execution is not None and isinstance(report.execution.result, dict):
            raw = report.execution.result.get("orderId")
            if raw is not None:
                exchange_order_id = str(raw)
        event = ExecutionAuditEvent.create(
            status=status,
            runtime_mode=config.mode.value,
            client_order_id=report.execution.client_order_id if report.execution else (order.client_order_id if order else ""),
            strategy_version_id=strategy_version_id,
            strategy_fingerprint=fingerprint,
            authorization_hash=auth_hash,
            risk_approved=risk_result.approved,
            occurred_at=self._clock(),
            reasons=report.reasons,
            exchange_order_id=exchange_order_id,
        )
        self._audit_sink.append(event)
