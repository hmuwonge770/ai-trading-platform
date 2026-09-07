# Autonomous Stage L — Controlled Testnet Orchestration

## Objective

Stage L connects the existing deterministic autonomous risk/execution pipeline to the controlled Binance Spot Testnet submitter as a complete orchestration cycle.

```text
Decision
  -> deterministic risk
  -> autonomous execution loop
  -> Testnet submitter
  -> Binance Spot Testnet
  -> execution outcome
  -> bounded recovery
```

## Mandatory gates

1. `AutonomousMode.TESTNET` must be selected.
2. The control plane must be `RUNNING` with trading enabled.
3. Kill switch must be disabled and circuit breaker closed.
4. Successful Testnet account preflight is required before processing.
5. Every candidate must pass the existing deterministic risk engine.
6. Execution continues through `AutonomousExecutionLoop`; the runner cannot bypass its idempotency and identity checks.
7. Execution outcomes are observed by the existing bounded recovery engine.
8. Risk rejection or missing preflight never reaches the exchange.

## Safety boundary

The runner has no exchange credentials and does not call Binance directly. The injected Testnet submitter remains responsible for the exchange boundary and its hard-wired Spot Testnet endpoint.

Testnet execution is opt-in. Existing fail-closed defaults remain unchanged, and this stage does not introduce production/live execution.

## Operational sequence

1. Configure Testnet credentials through the deployment secret mechanism.
2. Construct the Spot Testnet adapter and controlled submitter.
3. Set autonomous control explicitly to `TESTNET`, enable trading, disable the kill switch, and start it.
4. Run account preflight.
5. Feed decisions into the Testnet runner.
6. Observe risk, execution, recovery, reconciliation, and account state.
7. Stop opening new positions and investigate immediately if exchange state or accounting becomes uncertain.

## What this stage does not do

- It does not enable live Binance trading.
- It does not give an AI model direct exchange access.
- It does not bypass risk approval.
- It does not automatically promote strategies or increase capital limits.
- It does not claim profitability or production readiness.
