# Autonomous Stage B — Market Intelligence & Decision Engine

Stage B establishes the deterministic decision boundary for autonomous operation.

## Flow

```text
Market Snapshot
  -> Decision Policy
  -> BUY / SELL / HOLD
  -> Confidence Threshold
  -> Autonomous Control Plane
  -> later: Risk Gateway -> Order Intent -> Execution
```

The decision engine does not hold exchange credentials, call Binance, or submit orders.

## Decision model

A normalized market snapshot contains symbol, price, fast/slow EMA, RSI and timestamp. The initial deterministic policy produces:

- `BUY` when fast EMA is above slow EMA and RSI is not overbought.
- `SELL` when fast EMA is below slow EMA and RSI is not oversold.
- `HOLD` otherwise.

A minimum confidence threshold is mandatory. Decisions below the threshold fail closed to `HOLD`.

This is an initial engineering policy, not a claim of profitability. It is intentionally simple so the autonomous control path can be tested before adding model-driven market intelligence.

## Next stages

1. Continuous market-data ingestion and candle completion.
2. AI market-regime analysis and structured signal proposals.
3. Signal scoring and strategy selection.
4. Risk-aware order-intent generation.
5. Autonomous paper trading.
6. Testnet autonomous execution.
7. Live autonomous execution under explicit bounded policy.
