# Autonomous Stage C — Continuous Market Data & Signal Loop

Stage C connects normalized market observations to the autonomous decision boundary without granting the loop an order-submission capability.

## Flow

```text
Market-data adapter
  -> normalized MarketEvent
  -> closed-candle check
  -> freshness check
  -> event-id deduplication
  -> AutonomousControl.can_run()
  -> AutonomousDecisionEngine
  -> decision sink
  -> later: risk gateway -> order intent -> execution
```

## Guarantees

- **Fail closed:** stopped, disabled, kill-switched, or circuit-broken autonomy produces no decision.
- **Closed data only:** incomplete candles are ignored so an intrabar signal cannot be treated as a completed observation.
- **Fresh data only:** events older than the configured freshness window are ignored.
- **No future data:** observations timestamped in the future are ignored.
- **Idempotent processing:** repeated event IDs are evaluated at most once, with bounded in-memory deduplication.
- **Transport separation:** the loop consumes an async event source and does not own Binance credentials or order submission.

The loop is intentionally transport-agnostic. Binance WebSocket reconnect/recovery and candle normalization belong to the market-data adapter. This separation prevents transport failures from bypassing the autonomous control boundary.

## Current scope

Stage C evaluates already-normalized completed market events. It does not place exchange orders, size positions, or override the risk gateway.

## Next stage

Stage D will add autonomous AI market-regime analysis and structured signal proposals. Model output will remain advisory evidence; deterministic controls will continue to own the final decision boundary.
