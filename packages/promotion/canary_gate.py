from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CanaryGateReport:
    """Immutable evidence for the live-canary safety gate.

    A canary may advance only when every safety condition is clean. Counts are
    explicit rather than inferred from a generic health flag so a caller cannot
    accidentally hide an unresolved reconciliation or execution problem.
    """

    reconciliation_errors: int = 0
    unresolved_unknowns: int = 0
    balance_position_mismatches: int = 0
    risk_violations: int = 0
    critical_execution_errors: int = 0
    account_healthy: bool = True
    market_data_fresh: bool = True
    circuit_breaker_open: bool = False
    kill_switch: bool = False

    @property
    def passed(self) -> bool:
        return (
            self.reconciliation_errors == 0
            and self.unresolved_unknowns == 0
            and self.balance_position_mismatches == 0
            and self.risk_violations == 0
            and self.critical_execution_errors == 0
            and self.account_healthy
            and self.market_data_fresh
            and not self.circuit_breaker_open
            and not self.kill_switch
        )

    def failures(self) -> tuple[str, ...]:
        failures: list[str] = []
        if self.reconciliation_errors:
            failures.append("reconciliation errors are present")
        if self.unresolved_unknowns:
            failures.append("unresolved unknown orders are present")
        if self.balance_position_mismatches:
            failures.append("balance or position mismatches are present")
        if self.risk_violations:
            failures.append("risk violations are present")
        if self.critical_execution_errors:
            failures.append("critical execution errors are present")
        if not self.account_healthy:
            failures.append("trading account is unhealthy")
        if not self.market_data_fresh:
            failures.append("market data is stale")
        if self.circuit_breaker_open:
            failures.append("circuit breaker is open")
        if self.kill_switch:
            failures.append("kill switch is enabled")
        return tuple(failures)
