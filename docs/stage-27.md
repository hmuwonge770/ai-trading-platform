# Stage 27 — Failure & Property Testing

Stage 27 adds property-based and failure-injection coverage around the deterministic money and execution boundaries.

## Properties

- Balanced accounting transfers preserve zero aggregate asset imbalance.
- Repeated delivery of the same accounting reference remains idempotent.
- Repeated delivery of the same client order ID reaches the execution backend at most once.
- Backend failures are surfaced rather than converted into false execution success; a retry is possible because no success result is cached.
- Testnet execution remains bound to the Binance Spot Testnet endpoint.

Hypothesis is used with bounded example counts so CI remains deterministic and fast.

## Safety

These tests do not contact Binance and do not contain exchange credentials. Failure tests use synthetic backends only. The production Binance endpoint remains rejected by the Stage 17 testnet configuration.
