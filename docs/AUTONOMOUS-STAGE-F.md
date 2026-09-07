# Autonomous Stage F — Risk-Gated Execution Loop

Stage F connects the autonomous risk boundary to the existing execution abstraction without giving the AI direct exchange access.

## Flow

```text
AutonomousRiskResult
    -> approved OrderIntent + matching RiskDecision
    -> symbol/timeframe validation
    -> idempotency check
    -> injected ExecutionSubmitter
```

## Guarantees

- Unapproved risk results never reach the execution submitter.
- An approved result must contain both an `OrderIntent` and its matching risk decision.
- Order symbol and timeframe must match the market candle supplied to execution.
- Client order IDs are deduplicated with bounded memory.
- Execution transport is injected; this module has no Binance client or credentials.
- The existing execution service remains responsible for requiring an independently approved deterministic risk decision and preserving its own idempotency.

## Production boundary

This stage does not enable live trading by itself. A future production adapter must still enforce environment guards, authorization, kill switch/circuit breaker, reconciliation, and exchange-state validation before any live order is accepted.

## Verification

Unit tests cover approval gating, duplicate suppression, symbol/timeframe mismatch, and invalid configuration.
