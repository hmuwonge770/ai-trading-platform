# Stage AD — Autonomous Health State Machine

## Objective

Introduce a deterministic runtime health state machine that converts authorization, exchange-adapter, reconciliation, accounting, and kill-switch signals into a bounded health state.

## Five implementation phases

1. **Design & contract** — immutable observations, policy thresholds, and explicit health states.
2. **Core implementation** — deterministic HEALTHY/DEGRADED/HALTED transitions with consecutive-observation counters.
3. **Safety/control integration** — unsafe reconciliation/accounting/authorization/adapter state degrades or halts; an enabled kill switch halts immediately.
4. **Tests & failure scenarios** — recovery hysteresis, repeated failures, kill-switch behavior, invalid inputs, and immutable contracts.
5. **CI → merge → post-merge verification** — run lint/tests, merge only after green CI, then verify the main-branch workflow.

## State semantics

- `HALTED`: no autonomous execution should be considered safe.
- `DEGRADED`: an unsafe observation has occurred, but the configured halt threshold has not yet been reached.
- `HEALTHY`: all required runtime signals are healthy for the configured recovery window.

The state machine starts in `HALTED` by default and requires consecutive healthy observations before becoming `HEALTHY`.

## Safety boundary

This component is a control-plane health assessment only. It does not:

- submit, cancel, amend, or retry orders;
- obtain or store exchange credentials;
- approve or renew live authorization;
- change capital limits or risk policy;
- promote strategies;
- disable the kill switch.

A kill switch that is enabled forces `HALTED`; the state machine cannot turn it off. Runtime components remain responsible for enforcing their own execution gates.

## Default thresholds

- degrade after 1 consecutive unsafe observation;
- halt after 2 consecutive unsafe observations;
- recover to healthy after 2 consecutive healthy observations.

Thresholds are configurable but must be positive, with the halt threshold no lower than the degradation threshold.
