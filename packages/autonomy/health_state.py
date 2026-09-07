"""Deterministic autonomous runtime health state machine."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AutonomousHealthState(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    HALTED = "halted"


@dataclass(frozen=True, slots=True)
class HealthObservation:
    """Point-in-time safety signals used by the health state machine."""

    authorization_valid: bool
    adapter_healthy: bool
    reconciliation_healthy: bool
    accounting_healthy: bool
    kill_switch_enabled: bool
    observed_at: int

    def __post_init__(self) -> None:
        if self.observed_at <= 0:
            raise ValueError("observed_at must be positive")

    @property
    def safe(self) -> bool:
        return (
            self.authorization_valid
            and self.adapter_healthy
            and self.reconciliation_healthy
            and self.accounting_healthy
            and not self.kill_switch_enabled
        )

    @property
    def recoverable(self) -> bool:
        return (
            self.authorization_valid
            and self.adapter_healthy
            and self.reconciliation_healthy
            and self.accounting_healthy
        )


@dataclass(frozen=True, slots=True)
class HealthStatePolicy:
    """Consecutive-observation thresholds for deterministic transitions."""

    degraded_after: int = 1
    halted_after: int = 2
    healthy_after: int = 2

    def __post_init__(self) -> None:
        if min(self.degraded_after, self.halted_after, self.healthy_after) <= 0:
            raise ValueError("health thresholds must be positive")
        if self.halted_after < self.degraded_after:
            raise ValueError("halted_after must be >= degraded_after")


@dataclass(frozen=True, slots=True)
class HealthStateReport:
    state: AutonomousHealthState
    previous_state: AutonomousHealthState
    consecutive_unhealthy: int
    consecutive_healthy: int
    reason: str
    observed_at: int


class AutonomousHealthStateMachine:
    """Move monotonically toward safety when runtime health becomes unsafe."""

    def __init__(
        self,
        *,
        policy: HealthStatePolicy | None = None,
        initial_state: AutonomousHealthState = AutonomousHealthState.HALTED,
    ) -> None:
        self._policy = policy or HealthStatePolicy()
        self._state = initial_state
        self._consecutive_unhealthy = 0
        self._consecutive_healthy = 0

    @property
    def state(self) -> AutonomousHealthState:
        return self._state

    def observe(self, observation: HealthObservation) -> HealthStateReport:
        previous = self._state
        if observation.kill_switch_enabled or not observation.recoverable:
            self._consecutive_unhealthy += 1
            self._consecutive_healthy = 0
            if observation.kill_switch_enabled:
                self._state = AutonomousHealthState.HALTED
                reason = "kill_switch_enabled"
            elif self._consecutive_unhealthy >= self._policy.halted_after:
                self._state = AutonomousHealthState.HALTED
                reason = "repeated_unsafe_health"
            elif self._consecutive_unhealthy >= self._policy.degraded_after:
                self._state = AutonomousHealthState.DEGRADED
                reason = "unsafe_health"
            else:
                reason = "health_observation_unsafe"
        else:
            self._consecutive_unhealthy = 0
            self._consecutive_healthy += 1
            if self._consecutive_healthy >= self._policy.healthy_after:
                self._state = AutonomousHealthState.HEALTHY
                reason = "health_recovered"
            elif self._state is AutonomousHealthState.HALTED:
                reason = "recovery_pending"
            else:
                reason = "recovery_observation"

        return HealthStateReport(
            state=self._state,
            previous_state=previous,
            consecutive_unhealthy=self._consecutive_unhealthy,
            consecutive_healthy=self._consecutive_healthy,
            reason=reason,
            observed_at=observation.observed_at,
        )
