# Autonomous Stage Y — Controlled Live Runtime Orchestration

Stage Y composes the deployment-level live runtime guard with the existing
human-authorization and deterministic live execution boundary.

## Flow

`runtime config → control plane → authorization consumption → adapter preflight → risk result → live execution boundary`

Only the existing execution boundary receives an order-submission capability.
The orchestrator itself owns no exchange credentials and does not call Binance.

## Runtime modes

- `disabled`: blocks submission.
- `preflight`: evaluates gates but never submits.
- `dry_run`: evaluates gates but never submits.
- `enabled`: may delegate only when every runtime and execution gate passes.

## Required enabled conditions

- explicit `LIVE_RUNTIME_MODE=enabled`
- explicit `LIVE_EXECUTION_ENABLED=true`
- `LIVE_KILL_SWITCH=false`
- autonomous control is `LIVE`, `RUNNING`, trading-enabled, and not circuit-broken
- authorization consumption is authorized and fresh
- production live adapter preflight succeeds
- an immutable live authorization snapshot is present
- the deterministic risk result is approved

The final authorization, strategy identity, control, and duplicate-order checks
remain in `AutonomousLiveExecutionBoundary`.

## Safety

Stage Y does not approve promotions, renew authorization, change capital,
bypass risk controls, disable kill switches, or expose credentials. Disabled,
preflight, dry-run, blocked, expired, or missing-authorization states never
invoke the execution boundary.

The presence of a production adapter does not by itself enable live trading;
deployment configuration and the existing authorization/risk/control gates must
all explicitly permit delegation.
