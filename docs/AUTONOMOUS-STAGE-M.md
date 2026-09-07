# Autonomous Stage M — Testnet Reconciliation & Exchange-State Recovery

## Objective

Stage M adds a read-only reconciliation boundary between autonomous expectations and the observed Binance Spot Testnet state.

```text
Expected local state
        |
        v
Testnet state provider -> snapshot validation -> reconciliation
                                      |
                    +-----------------+----------------+
                    |                                  |
                  match                            mismatch
                    |                                  |
                 continue                         fail closed
                                                       |
                                                       v
                                                recovery HALT
```

## Mandatory safety properties

1. Reconciliation consumes an injected state provider; it has no exchange credentials.
2. Reconciliation never submits, cancels, or amends an order.
3. Snapshots older than the configured freshness bound are rejected.
4. Missing expected orders, unknown orders, symbol mismatches, quantity mismatches, and status mismatches are unsafe.
5. Provider/transport failures are treated as unavailable exchange state and halt recovery.
6. Any reconciliation mismatch is routed to the existing `AutonomousRecoveryEngine` as a fail-closed event.
7. Recovery may only be reset after a successful external reconciliation.
8. This stage is Testnet-only in the autonomous lifecycle and does not enable live trading.

## Operational sequence

1. Obtain an authenticated Spot Testnet snapshot through the existing Testnet adapter.
2. Build expected state from locally accepted autonomous execution records.
3. Reconcile before resuming autonomous processing after an interruption or uncertain execution.
4. Keep autonomous processing halted whenever reconciliation is unhealthy.
5. Investigate and correct the underlying state mismatch before resetting recovery.

## What this stage does not do

- It does not place recovery orders automatically.
- It does not cancel unknown orders automatically.
- It does not modify balances or positions.
- It does not bypass risk, authorization, endpoint, or kill-switch controls.
- It does not enable production/live execution.
- It does not claim profitability or production readiness.
