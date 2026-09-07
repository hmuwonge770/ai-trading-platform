# Autonomous Stage E — Deterministic Autonomous Risk Engine

Stage E places a deterministic risk boundary between an AI decision and any future execution adapter.

## Flow

```text
AI Decision
    -> decision freshness
    -> HOLD rejection
    -> order-rate policy
    -> liquidity participation policy
    -> OrderIntent candidate
    -> existing RiskGateway
    -> approved/rejected risk result
```

## Controls

- HOLD decisions can never become orders.
- Future-dated and stale decisions fail closed.
- Order quantity must be positive.
- A bounded order-rate window limits autonomous order creation.
- Order notional is bounded by a configured fraction of observed quote liquidity.
- Existing `RiskGateway` remains authoritative for order notional, position, exposure, daily loss, cash, and position checks.
- A gateway rejection is final and is never overridden by the autonomous layer.
- This stage creates an `OrderIntent` candidate only; it does not call an exchange or execution backend.

## Safety boundary

The autonomous risk engine does not receive exchange credentials and does not submit orders. Later execution stages must consume only risk-approved intents and continue to enforce execution authorization, idempotency, reconciliation, and circuit breakers.

## Verification

Unit tests cover valid approval, HOLD rejection, stale decisions, liquidity limits, order-rate limits, and preservation of the existing gateway's final rejection.
