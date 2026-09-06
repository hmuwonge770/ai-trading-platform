# Stage 28 — 72-hour Soak Testing

Stage 28 adds an accelerated, deterministic 72-hour reliability soak. It uses virtual time so CI can exercise the full 72-hour interval without sleeping for 72 real hours.

## Coverage

- 432 ten-minute virtual ticks over exactly 72 hours.
- Deterministic injected failures at several points in the run.
- Retry of failed delivery using the same idempotency identity.
- Duplicate-event detection.
- Non-negative and bounded state invariants on every tick.
- Explicit timezone-aware start validation.

## Interpretation

A green CI run proves that the modeled reliability loop survives the configured virtual 72-hour workload and injected faults. It does **not** claim that the production system has physically run for 72 hours. A real 72-hour environment soak remains a deployment-readiness activity and is intentionally separate from unit CI.

## Safety

The harness is exchange-free. It does not contact Binance, use credentials, place orders, or enable live trading. It is intended to validate deterministic reliability behavior before Kubernetes isolation and production-readiness stages.
