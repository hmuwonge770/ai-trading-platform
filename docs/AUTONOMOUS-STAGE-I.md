# Autonomous Stage I — Reliability & Recovery

## Purpose

Stage I adds a deterministic reliability boundary around autonomous operation. Operational faults must produce bounded recovery decisions and must never weaken the existing risk, reconciliation, authorization, or kill-switch controls.

## Recovery states

- `continue`: the observed condition is healthy or safely resolved.
- `retry`: a transient execution failure may be retried within the configured bounded budget.
- `halt`: autonomous operation must stop fail-closed.

## Safety rules

- Reconciliation mismatches halt immediately.
- Unknown failures halt immediately.
- Missing or invalid market-age information halts immediately.
- Stale market data halts autonomous operation.
- Execution failures have a finite retry budget and a finite consecutive-failure threshold.
- A halted engine cannot be resumed by observing a success event.
- Reset after a halt explicitly represents successful external reconciliation.
- The recovery engine does not submit orders, alter risk limits, bypass authorization, or disable the kill switch.

## Integration boundary

The engine is intentionally a decision component. A runtime supervisor can translate `halt` into the existing autonomous control-plane halt/kill-switch path and can perform reconciliation before calling `reset_after_reconciliation()`.

Retries remain subject to the normal execution identity, risk gateway, authorization, and exchange controls. This stage does not make live trading safer by bypassing those gates; it makes operational failure handling explicit and bounded.
