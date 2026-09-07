"""Controlled orchestration for the future autonomous live execution path.

This layer composes the deployment runtime guard with the existing live
execution boundary. It never owns credentials and never bypasses authorization,
risk, control-plane, or adapter preflight gates.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .authorization_consumption import AuthorizationConsumptionReport, LiveExecutionAuthorization
from .control import AutonomousControl
from .live_execution import AutonomousLiveExecutionBoundary, LiveExecutionReport, LiveExecutionStatus
from .live_runtime import LiveAdapterPreflightContext, LiveRuntimeConfig, LiveRuntimeMode, AutonomousLiveRuntimeGuard
from .risk import AutonomousRiskResult


class LiveOrchestrationStatus(StrEnum):
    SUBMITTED = "submitted"
    BLOCKED = "blocked"
    DRY_RUN = "dry_run"
    PREFLIGHT = "preflight"


@dataclass(frozen=True, slots=True)
class LiveOrchestrationReport:
    status: LiveOrchestrationStatus
    runtime: object
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
    ) -> None:
        self._runtime_guard = runtime_guard
        self._execution_boundary = execution_boundary

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
            return LiveOrchestrationReport(
                LiveOrchestrationStatus.PREFLIGHT,
                runtime,
                None,
                runtime.reasons,
            )
        if config.mode is LiveRuntimeMode.DRY_RUN:
            return LiveOrchestrationReport(
                LiveOrchestrationStatus.DRY_RUN,
                runtime,
                None,
                runtime.reasons,
            )
        if not runtime.submit_allowed:
            return LiveOrchestrationReport(
                LiveOrchestrationStatus.BLOCKED,
                runtime,
                None,
                runtime.reasons,
            )
        if authorization_snapshot is None:
            return LiveOrchestrationReport(
                LiveOrchestrationStatus.BLOCKED,
                runtime,
                None,
                ("live_authorization_snapshot_missing",),
            )

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
        return LiveOrchestrationReport(status, runtime, execution, execution.reasons)
