# Stage AW — Production Readiness Review

## Purpose

AW establishes a deterministic final readiness review before controlled production expansion. It is a control-plane gate only.

## Implementation phases

1. Immutable production-readiness contract.
2. Deterministic readiness assessment across soak, failure, SLO, security, incident-recovery, operator-approval, and runtime-preflight evidence.
3. Governance integration with strategy identity binding.
4. Boundary, failure, determinism, and regression tests.
5. Package exports and documentation.
6. CI, merge, post-merge verification, and roadmap advancement.

## Safety boundaries

- No Binance credentials are accepted or exposed.
- No exchange orders are submitted.
- No live runtime is enabled by the readiness evaluator.
- No capital or risk ceiling can be increased.
- No kill switch or circuit breaker can be bypassed.
- Strategy identity is mandatory.
- Missing or failed required evidence blocks readiness.
- Operator approval remains an explicit prerequisite.
- Runtime preflight remains an explicit prerequisite.

A `READY` assessment means the evidence satisfies the configured readiness contract. It is not itself authorization to execute live orders.
