# Autonomous Trading — Stage U

## Live Execution Boundary

Stage U establishes the final deterministic software boundary before a separately supplied live exchange adapter can receive an order.

### Required inputs

The boundary accepts all of the following:

1. A `LiveExecutionAuthorization` produced by the Stage T consumption contract.
2. An `AutonomousRiskResult` that is explicitly approved and contains an `OrderIntent`.
3. An `AutonomousControl` snapshot that is explicitly running in `LIVE` mode with trading enabled, kill switch disabled, and circuit breaker closed.
4. An injected `LiveExecutionSubmitter` capability.

### Fail-closed checks

The boundary blocks submission when:

- deterministic risk has not approved the order;
- the autonomous control plane is not runnable;
- the control mode is not `LIVE`;
- the authorization environment is not a permitted live promotion stage;
- the authorization hash is missing;
- the order strategy version differs from the authorized strategy version;
- the client order ID is missing; or
- the client order ID was already submitted through this boundary instance.

Submitter exceptions are converted into a blocked result and are never treated as successful execution.

### Safety properties

- The boundary owns no Binance credentials.
- The boundary does not construct an exchange client.
- The boundary does not approve, renew, activate, or mutate authorization.
- The boundary cannot bypass deterministic risk controls.
- The boundary cannot disable the kill switch or circuit breaker.
- The boundary does not increase capital allocation.
- Duplicate client order IDs are suppressed.
- A live adapter must be injected explicitly; there is no default exchange implementation.
- The existing reconciliation, accounting, recovery, and authorization controls remain upstream requirements.

A successful `SUBMITTED` result means only that the injected capability accepted the order. It is not a claim that an exchange filled the order. Exchange acknowledgement, reconciliation, accounting, and recovery remain separate responsibilities.

## Current posture

Stage U does **not** enable live trading by itself. The repository remains fail-closed unless an independently authorized runtime explicitly supplies the required live control state, authorization, risk approval, and exchange capability.

## Next stage

The next stage can integrate the boundary with a tightly scoped live adapter contract while preserving credential isolation, order-level risk checks, reconciliation, recovery, and explicit human authorization.
