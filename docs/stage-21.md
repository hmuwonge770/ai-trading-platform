# Stage 21 — Security, Failure & Soak Testing

Stage 21 hardens the boundary between research, trading authorization, exchange access, and durable state.

## Security controls

- Research contexts reject exchange credentials and private-key fields.
- Live execution is disabled by default by the security policy.
- Testnet execution is restricted to the Binance Spot Testnet endpoint.
- Paper execution cannot use Binance order endpoints.
- Common credential fields are redacted before logging or telemetry.
- Existing trading-environment validation remains fail-closed.

## Failure injection

`FailurePlan` provides deterministic, seed-free failure points for reliability tests. Tests can fail specific invocation numbers and assert retry, idempotency, and recovery behavior without touching an exchange.

## Soak coverage

The Stage 21 suite repeatedly posts the same accounting transaction to verify that at-least-once delivery does not duplicate financial effects. It also exercises repeated deterministic failure checkpoints to verify failures remain observable over a longer run.

No Stage 21 test contacts Binance, requires exchange credentials, or permits AI/research code to submit orders.
