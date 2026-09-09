# Stage AU — Security Hardening

## Objective

Establish a deterministic security gate for the autonomous trading control plane before later production-expansion stages.

## Implementation phases

1. Security contract and immutable policy requirements.
2. Deterministic security observation and assessment.
3. Security governance integration with strategy identity binding.
4. Boundary, failure, deterministic and regression tests.
5. Public package exports and documentation.
6. CI, merge, post-merge verification and roadmap advancement.

## Required controls

- Exchange secrets remain isolated from the AI decision plane.
- Strategy artifacts must satisfy the configured verification requirement.
- Audit integrity must be verified before security is considered ready.
- Dependency integrity must be verified.
- A hard operator shutdown capability must remain available.
- Strategy identity and version must be present at the governance boundary.

## Safety boundary

AU is a control-plane assessment. It does not retrieve secrets, call Binance, submit orders, enable live runtime execution, widen risk or capital limits, disable the kill switch, mutate strategy state, or autonomously remediate infrastructure.

Any required security control that is not verified results in `BLOCKED`. Missing strategy identity also fails closed. Assessment output is deterministic and read-only.
