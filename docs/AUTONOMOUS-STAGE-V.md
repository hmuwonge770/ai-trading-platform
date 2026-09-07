# Autonomous Trading — Stage V

## Credential-Isolated Live Adapter Preflight

Stage V defines a preflight contract for a future live exchange adapter. It validates that the runtime is targeting the explicitly approved production endpoint, has an opaque credential reference, has an enabled account, and has passed an adapter healthcheck.

The autonomy layer never receives raw API keys or secrets. The credential reference is only an identifier for an external secret-management mechanism.

The preflight is read-only and never submits, cancels, or modifies an order. It also blocks Testnet and sandbox endpoints.

A `READY` report means the adapter configuration satisfies this narrow preflight contract. It does not authorize trading, approve capital, or replace Stage R/S/T/U authorization, risk, reconciliation, accounting, recovery, kill-switch, or circuit-breaker controls.

## Safety

No Binance client or credentials are created by this stage. A future adapter must remain separately injected and subject to the Stage U execution boundary.
