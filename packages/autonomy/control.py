"""Fail-closed control state for autonomous trading."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AutonomousMode(StrEnum):
    DISABLED = "DISABLED"
    PAPER = "PAPER"
    TESTNET = "TESTNET"
    LIVE = "LIVE"


class AutonomousState(StrEnum):
    STOPPED = "STOPPED"
    RUNNING = "RUNNING"
    HALTED = "HALTED"


@dataclass(frozen=True, slots=True)
class AutonomousControl:
    """Immutable snapshot of the autonomous operating boundary.

    This object contains policy state only. It does not hold credentials,
    exchange clients, or an order-submission capability.
    """

    mode: AutonomousMode = AutonomousMode.DISABLED
    state: AutonomousState = AutonomousState.STOPPED
    trading_enabled: bool = False
    kill_switch_enabled: bool = True
    circuit_breaker_open: bool = False

    def can_run(self) -> bool:
        """Return whether the autonomous decision loop may execute."""
        return (
            self.state is AutonomousState.RUNNING
            and self.mode is not AutonomousMode.DISABLED
            and self.trading_enabled
            and not self.kill_switch_enabled
            and not self.circuit_breaker_open
        )

    def can_open_position(self) -> bool:
        """Return whether autonomous logic may propose a new position."""
        return self.can_run()

    def start(self) -> "AutonomousControl":
        if self.mode is AutonomousMode.DISABLED:
            raise ValueError("autonomous mode is disabled")
        if self.kill_switch_enabled:
            raise ValueError("kill switch is enabled")
        if self.circuit_breaker_open:
            raise ValueError("circuit breaker is open")
        if not self.trading_enabled:
            raise ValueError("trading is disabled")
        return AutonomousControl(
            mode=self.mode,
            state=AutonomousState.RUNNING,
            trading_enabled=self.trading_enabled,
            kill_switch_enabled=self.kill_switch_enabled,
            circuit_breaker_open=self.circuit_breaker_open,
        )

    def stop(self) -> "AutonomousControl":
        return AutonomousControl(
            mode=self.mode,
            state=AutonomousState.STOPPED,
            trading_enabled=self.trading_enabled,
            kill_switch_enabled=self.kill_switch_enabled,
            circuit_breaker_open=self.circuit_breaker_open,
        )

    def halt(self) -> "AutonomousControl":
        return AutonomousControl(
            mode=self.mode,
            state=AutonomousState.HALTED,
            trading_enabled=self.trading_enabled,
            kill_switch_enabled=True,
            circuit_breaker_open=True,
        )

    def with_mode(self, mode: AutonomousMode) -> "AutonomousControl":
        if mode is AutonomousMode.DISABLED:
            return AutonomousControl()
        return AutonomousControl(
            mode=mode,
            state=AutonomousState.STOPPED,
            trading_enabled=self.trading_enabled,
            kill_switch_enabled=self.kill_switch_enabled,
            circuit_breaker_open=self.circuit_breaker_open,
        )

    def with_trading(self, enabled: bool) -> "AutonomousControl":
        return AutonomousControl(
            mode=self.mode,
            state=self.state if enabled else AutonomousState.STOPPED,
            trading_enabled=enabled,
            kill_switch_enabled=self.kill_switch_enabled,
            circuit_breaker_open=self.circuit_breaker_open,
        )

    def with_kill_switch(self, enabled: bool) -> "AutonomousControl":
        return AutonomousControl(
            mode=self.mode,
            state=AutonomousState.STOPPED if enabled else self.state,
            trading_enabled=self.trading_enabled,
            kill_switch_enabled=enabled,
            circuit_breaker_open=self.circuit_breaker_open,
        )

    def with_circuit_breaker(self, opened: bool) -> "AutonomousControl":
        return AutonomousControl(
            mode=self.mode,
            state=AutonomousState.HALTED if opened else AutonomousState.STOPPED,
            trading_enabled=self.trading_enabled,
            kill_switch_enabled=self.kill_switch_enabled or opened,
            circuit_breaker_open=opened,
        )
