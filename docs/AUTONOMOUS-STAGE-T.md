# Autonomous Trading — Stage T

## Live Authorization Consumption Guard

Stage T adds the final read-only boundary between an existing human-authorized live authorization snapshot and any future live execution consumer.

The consumer validates the Stage S freshness result and independently compares the immutable snapshot with the persisted `AuthorizationRecord` before producing an immutable `LiveExecutionAuthorization` value.

### Required checks

- authorization freshness must be `VALID`;
- the persisted authorization hash must exactly match the snapshot hash;
- persisted promotion state and all authorization identities must match;
- persisted expiry must exactly match the immutable snapshot expiry; and
- the authorized environment must be a live promotion stage.

Any mismatch blocks consumption. An expired authorization is explicitly reported as `EXPIRED`.

### Safety properties

- The consumer does not approve, activate, renew, or mutate a promotion.
- It does not submit, cancel, amend, or repair orders.
- It owns no exchange client or credentials.
- It cannot bypass the deterministic risk gateway, reconciliation, accounting, recovery, kill switch, or circuit breaker.
- It creates no new authority; it only materializes an immutable handoff when existing authority is still valid.
- No live execution is enabled by this stage.

### Boundary contract

A future live execution adapter must accept the immutable authorization handoff and continue to enforce its own order-level risk and execution controls. It must not treat a stale, expired, mismatched, or absent handoff as permission to trade.

The current system therefore remains fail closed: Stage T establishes the authorization-consumption contract without connecting the autonomous runner to live Binance execution.
