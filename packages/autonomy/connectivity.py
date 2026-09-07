"""Credential-free exchange connectivity resilience primitives."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class ConnectivityState(StrEnum):
    ONLINE = "online"
    DEGRADED = "degraded"
    OFFLINE = "offline"


class ConnectivityProbe(Protocol):
    """Application-owned connectivity check; implementations own transport."""

    def check(self) -> bool: ...


@dataclass(frozen=True, slots=True)
class ConnectivityPolicy:
    degraded_after: int = 1
    offline_after: int = 3
    online_after: int = 2

    def __post_init__(self) -> None:
        if min(self.degraded_after, self.offline_after, self.online_after) <= 0:
            raise ValueError("connectivity thresholds must be positive")
        if self.offline_after < self.degraded_after:
            raise ValueError("offline_after must be >= degraded_after")


@dataclass(frozen=True, slots=True)
class ConnectivityReport:
    state: ConnectivityState
    previous_state: ConnectivityState
    consecutive_failures: int
    consecutive_successes: int
    reason: str


class AutonomousConnectivityMonitor:
    """Track exchange reachability without retrying or mutating orders."""

    def __init__(
        self,
        *,
        probe: ConnectivityProbe,
        policy: ConnectivityPolicy | None = None,
        initial_state: ConnectivityState = ConnectivityState.OFFLINE,
    ) -> None:
        self._probe = probe
        self._policy = policy or ConnectivityPolicy()
        self._state = initial_state
        self._consecutive_failures = 0
        self._consecutive_successes = 0

    @property
    def state(self) -> ConnectivityState:
        return self._state

    def check(self) -> ConnectivityReport:
        previous = self._state
        try:
            reachable = bool(self._probe.check())
        except Exception:
            reachable = False

        if not reachable:
            self._consecutive_failures += 1
            self._consecutive_successes = 0
            if self._consecutive_failures >= self._policy.offline_after:
                self._state = ConnectivityState.OFFLINE
                reason = "repeated_connectivity_failure"
            elif self._consecutive_failures >= self._policy.degraded_after:
                self._state = ConnectivityState.DEGRADED
                reason = "connectivity_failure"
            else:
                reason = "connectivity_check_failed"
        else:
            self._consecutive_failures = 0
            self._consecutive_successes += 1
            if self._consecutive_successes >= self._policy.online_after:
                self._state = ConnectivityState.ONLINE
                reason = "connectivity_recovered"
            elif self._state is ConnectivityState.OFFLINE:
                reason = "recovery_pending"
            else:
                reason = "connectivity_observation"

        return ConnectivityReport(
            state=self._state,
            previous_state=previous,
            consecutive_failures=self._consecutive_failures,
            consecutive_successes=self._consecutive_successes,
            reason=reason,
        )
