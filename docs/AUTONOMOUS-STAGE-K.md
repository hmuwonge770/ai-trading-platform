# Autonomous Stage K — Controlled Binance Spot Testnet Execution

## Objective

Stage K connects the autonomous execution boundary to the existing Binance Spot Testnet adapter. It permits autonomous order submission only in an explicitly enabled Testnet control state.

## Execution path

```text
AI / deterministic signal
        |
        v
Autonomous risk engine
        |
        v
Autonomous execution loop
        |
        v
Testnet control + account preflight
        |
        v
Binance Spot Testnet adapter
        |
        v
Testnet order response
```

## Mandatory gates

1. `AutonomousMode.TESTNET` must be selected.
2. The autonomous control state must be `RUNNING`.
3. Autonomous trading must be enabled.
4. The kill switch must be disabled.
5. The circuit breaker must be closed.
6. The order must have an independent approved `RiskDecision`.
7. The risk decision order ID must match the client order ID.
8. The order symbol and timeframe must match the execution candle.
9. Testnet account preflight must succeed before the first order.
10. Exchange failures must be returned as execution failures, never as false success.

## Endpoint isolation

The existing Binance adapter is hard-wired to `https://testnet.binance.vision` and rejects other base URLs. The autonomous Testnet submitter does not accept a production endpoint override.

Credentials remain confined to the exchange adapter configuration. They must be supplied through the deployment secret mechanism; never commit API keys or secrets to source control.

## Idempotency

`AutonomousExecutionLoop` remains the first-line client-order-ID deduplication boundary. The underlying execution service also provides exactly-once handling for a client order ID. This stage does not bypass those controls.

## Default posture

This stage does **not** enable Testnet trading by default. Existing fail-closed defaults remain unchanged. A deployment must explicitly configure Testnet credentials and explicitly move the autonomous control plane into a safe running Testnet state.

## What this stage does not do

- It does not enable Binance production/live trading.
- It does not expose credentials to AI models or research code.
- It does not bypass deterministic risk approval.
- It does not change strategy promotion or governance rules.
- It does not claim profitability or production readiness.

## Operational sequence

Before using Testnet autonomous execution:

1. Configure Binance Spot Testnet credentials in the secret store.
2. Verify the endpoint is the Spot Testnet endpoint.
3. Run account preflight (`ping` plus authenticated account check).
4. Confirm risk limits and reconciliation state.
5. Explicitly enable autonomous Testnet mode and start the control plane.
6. Observe execution outcomes and recovery events.
7. Stop or halt immediately on reconciliation mismatch, unexpected execution behavior, or other safety incident.

Stage K is a controlled integration test boundary, not authorization for live capital deployment.
