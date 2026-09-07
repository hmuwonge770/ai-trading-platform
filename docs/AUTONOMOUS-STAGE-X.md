# Autonomous Trading Stage X — Live Runtime Controls

## Purpose

Stage X adds the deployment-level control boundary around the production live adapter. It makes the runtime explicitly configurable as `disabled`, `preflight`, `dry_run`, or `enabled`, with fail-closed defaults.

## Runtime modes

- `disabled` — no live execution path is permitted.
- `preflight` — validate deployment, control, authorization, and adapter readiness; never submit.
- `dry_run` — exercise the same readiness boundary without permitting submission.
- `enabled` — submission is permitted only when every required gate passes.

## Required gates for enabled mode

1. `LIVE_RUNTIME_MODE=enabled`.
2. `LIVE_EXECUTION_ENABLED=true`.
3. `LIVE_KILL_SWITCH=false`.
4. Autonomous control is explicitly `LIVE`, `RUNNING`, trading-enabled, with its kill switch disabled and circuit breaker closed.
5. The Stage S/T authorization consumer reports `AUTHORIZED`.
6. The production Binance adapter passes its preflight and healthcheck.

Any failure blocks submission. Authorization is never renewed or mutated by this layer.

## Environment configuration

The loader accepts:

```text
LIVE_RUNTIME_MODE=disabled|preflight|dry_run|enabled
LIVE_EXECUTION_ENABLED=false
LIVE_KILL_SWITCH=true
```

The defaults are deliberately safe. Invalid mode or boolean values fail closed rather than being guessed.

## Safety boundary

Stage X does not contain credentials, approve promotions, disable the kill switch, change capital allocation, or submit orders. `preflight` and `dry_run` can report readiness but have `submit_allowed=false`. The production adapter remains behind the existing authorization, risk, reconciliation, accounting, recovery, and control-plane gates.

A deployment should therefore move through `preflight` and `dry_run` before any explicitly authorized `enabled` configuration is considered. This stage does **not** turn live trading on by default and makes no claim of profitability or production readiness.
