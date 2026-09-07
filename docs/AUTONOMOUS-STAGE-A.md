# Autonomous Stage A — Control Plane

Stage A introduces the control boundary required before the platform can run an autonomous decision loop.

## Safety defaults

A new `AutonomousControl` starts with:

- mode: `DISABLED`
- state: `STOPPED`
- trading: disabled
- kill switch: enabled
- circuit breaker: closed

Autonomous execution is therefore unavailable until every prerequisite is explicitly satisfied.

## Modes

- `DISABLED` — autonomous operation unavailable.
- `PAPER` — autonomous decisions may operate against the simulator when enabled.
- `TESTNET` — autonomous decisions may operate against Binance Spot Testnet when separately configured and authorized.
- `LIVE` — reserved for the later autonomous-live stages; this stage does not grant live execution authority.

## State transitions

```text
STOPPED -> RUNNING
RUNNING -> STOPPED
RUNNING -> HALTED
HALTED  -> STOPPED (only through an explicit controlled reset in a later control service)
```

Starting requires a non-disabled mode, trading enabled, kill switch disabled, and circuit breaker closed.

Opening a new position requires the same running state. The control object itself has no exchange client and no credential access.

## Next stage

Stage B will add continuous market observation and freshness-controlled market context. It must consume this boundary rather than creating an independent path around it.
