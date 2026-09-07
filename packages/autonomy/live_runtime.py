"""Deployment-level controls for the future live execution runtime.

The runtime defaults to preflight/disabled and never enables live execution from
application state alone. A deployment must explicitly opt in, while the
existing authorization, control-plane, and adapter gates remain mandatory.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .authorization_consumption import (
    AuthorizationConsumptionReport,
    AuthorizationConsumptionStatus,
)
from .control import AutonomousControl, AutonomousMode
from .live_adapter import AutonomousLiveAdapterPreflight, LiveAdapterPreflightContext


class LiveRuntimeMode(StrEnum):
    DISABLED = "disabled"
    PREFLIGHT = "preflight"
    DRY_RUN = "dry_run"
    ENABLED = "enabled"


@dataclass(frozen=True, slots=True)
class LiveRuntimeConfig:
    """Explicit deployment controls; safe defaults are intentional."""

    mode: LiveRuntimeMode = LiveRuntimeMode.DISABLED
    execution_enabled: bool = False
    kill_switch: bool = True

    @classmethod
    def from_environment(cls, environ: dict[str, str]) -> "LiveRuntimeConfig":
        """Load only explicit boolean values; invalid configuration fails closed."""
        raw_mode = environ.get("LIVE_RUNTIME_MODE", LiveRuntimeMode.DISABLED.value).strip().lower()
        try:
            mode = LiveRuntimeMode(raw_mode)
        except ValueError as exc:
            raise ValueError("LIVE_RUNTIME_MODE must be disabled, preflight, dry_run, or enabled") from exc

        def flag(name: str, default: bool) -> bool:
            raw = environ.get(name, "true" if default else "false").strip().lower()
            if raw not in {"true", "false"}:
                raise ValueError(f"{name} must be true or false")
            return raw == "true"

        return cls(
            mode=mode,
            execution_enabled=flag("LIVE_EXECUTION_ENABLED", False),
            kill_switch=flag("LIVE_KILL_SWITCH", True),
        )


@dataclass(frozen=True, slots=True)
class LiveRuntimeReport:
    mode: LiveRuntimeMode
    ready: bool
    submit_allowed: bool
    reasons: tuple[str, ...]


class AutonomousLiveRuntimeGuard:
    """Final deployment-level gate before a live adapter may be used."""

    def __init__(self, *, adapter_preflight: AutonomousLiveAdapterPreflight | None = None) -> None:
        self._adapter_preflight = adapter_preflight or AutonomousLiveAdapterPreflight()

    def assess(
        self,
        config: LiveRuntimeConfig,
        control: AutonomousControl,
        authorization: AuthorizationConsumptionReport,
        adapter: LiveAdapterPreflightContext,
    ) -> LiveRuntimeReport:
        reasons: list[str] = []

        if config.mode is LiveRuntimeMode.DISABLED:
            reasons.append("runtime_disabled")
        if config.kill_switch:
            reasons.append("deployment_kill_switch_enabled")
        if not config.execution_enabled:
            reasons.append("live_execution_not_explicitly_enabled")
        if control.mode is not AutonomousMode.LIVE:
            reasons.append("autonomous_control_not_live")
        if not control.can_run():
            reasons.append("autonomous_control_not_running")
        if authorization.status is AuthorizationConsumptionStatus.EXPIRED:
            reasons.append("live_authorization_expired")
        elif authorization.status is not AuthorizationConsumptionStatus.AUTHORIZED:
            reasons.append("live_authorization_not_authorized")

        adapter_report = self._adapter_preflight.assess(adapter)
        if not adapter_report.ready:
            reasons.extend(adapter_report.reasons)

        if config.mode is LiveRuntimeMode.PREFLIGHT:
            return LiveRuntimeReport(config.mode, not reasons, False, tuple(dict.fromkeys(reasons)))
        if config.mode is LiveRuntimeMode.DRY_RUN:
            return LiveRuntimeReport(config.mode, not reasons, False, tuple(dict.fromkeys(reasons)))

        return LiveRuntimeReport(
            config.mode,
            not reasons,
            not reasons and config.mode is LiveRuntimeMode.ENABLED,
            tuple(dict.fromkeys(reasons)),
        )
