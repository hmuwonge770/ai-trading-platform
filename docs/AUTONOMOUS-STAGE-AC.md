# Autonomous Stage AC — Durable Alert & Incident Lifecycle

## Objective

Turn operational alerts into a durable incident lifecycle without giving the monitoring or notification plane any trading authority.

## Phases

1. **Contract:** immutable incident identity, severity, fingerprint, timestamps, and lifecycle status.
2. **Persistence boundary:** application-owned store protocol; autonomy does not own infrastructure credentials.
3. **Lifecycle:** monotonic OPEN -> ACKNOWLEDGED/ESCALATED -> RESOLVED transitions.
4. **Failure validation:** invalid identity, timestamps, reopening, and malformed state fail closed.
5. **CI and promotion:** unit tests, lint, CI, merge, and post-merge verification are mandatory.

## Safety

Incident persistence and lifecycle state cannot submit, cancel, amend, retry, authorize, promote, allocate capital, or mutate risk policy. Resolved incidents cannot be reopened through this lifecycle contract. Durable infrastructure is supplied by the application layer.
