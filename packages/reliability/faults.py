from __future__ import annotations

from dataclasses import dataclass, field


class InjectedFailure(RuntimeError):
    """A deliberate fault used by reliability tests."""


@dataclass(slots=True)
class FailurePlan:
    """Fail deterministically on configured 1-based invocation numbers."""

    fail_on: frozenset[int] = frozenset()
    _calls: int = field(default=0, init=False)

    def checkpoint(self, operation: str = "operation") -> None:
        self._calls += 1
        if self._calls in self.fail_on:
            raise InjectedFailure(f"injected failure in {operation} at attempt {self._calls}")

    @property
    def calls(self) -> int:
        return self._calls
