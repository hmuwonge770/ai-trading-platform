# Autonomous Stage N — Testnet Accounting Integrity

## Objective

Add a read-only, fail-closed accounting reconciliation boundary for autonomous Binance Spot Testnet operation. The reconciler compares locally expected balances and positions with an injected Testnet snapshot before autonomous operation can rely on that state.

## Safety properties

1. **Testnet/accounting only** — this stage does not enable live trading.
2. **Read-only** — reconciliation never submits, cancels, or amends orders.
3. **Freshness required** — snapshots from the future or older than the configured limit are unsafe.
4. **Exact asset coverage** — missing and unexpected balances are mismatches.
5. **Exact position coverage** — missing and unexpected positions are mismatches.
6. **Decimal-safe quantities** — comparisons use `Decimal` and an explicit non-negative tolerance.
7. **Fail closed** — provider failures, invalid time, stale state, and accounting mismatches are unsafe.
8. **Recovery integration** — unsafe accounting state is routed to the existing bounded recovery engine.
9. **No credential ownership** — the accounting layer receives state through an injected provider.
10. **No automatic repair** — it does not mutate balances, positions, orders, or local accounting records.

## Expected vs observed state

The local system supplies:

- expected free and locked quantity for each tracked asset;
- expected quantity for each tracked spot position.

The Testnet state provider supplies one timestamped snapshot containing observed balances and positions.

The reconciler requires the two sets to match exactly, apart from the configured quantity tolerance. Any missing, unexpected, or materially different item is unsafe.

## Operational sequence

1. Obtain a timestamped Testnet accounting snapshot.
2. Reject provider errors and invalid/future/stale snapshots.
3. Compare all expected balances with observed balances.
4. Reject unexpected exchange assets.
5. Compare all expected positions with observed positions.
6. Reject unexpected exchange positions.
7. If all checks pass, report `HEALTHY`.
8. Otherwise report `MISMATCH`/`STALE`/`UNAVAILABLE` and route the condition to bounded recovery.

## Non-goals

- No live exchange integration.
- No automatic balance transfers or position repair.
- No order submission, cancellation, or amendment.
- No strategy promotion or model mutation.
- No profitability claims.
- No removal of existing control, risk, reconciliation, recovery, or kill-switch gates.

The default runtime posture remains unchanged: autonomous trading is disabled unless explicitly configured and all existing gates are satisfied.
