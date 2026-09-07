# Autonomous Stage H — Continuous Strategy Learning & Drift Detection

## Purpose

Stage H adds a deterministic observation layer for autonomous strategy performance. It evaluates realized return, drawdown, win rate, and sample size against an explicit policy.

## Decision states

- `continue`: observed behavior remains inside policy bounds.
- `review`: behavior has drifted or the sample is too small for confidence.
- `retire_candidate`: sufficiently large samples show severe degradation.

## Safety boundary

The learning engine is deliberately advisory. It **does not** mutate an immutable strategy version, change capital limits, disable controls, promote a strategy, or submit an order. A retirement candidate requires the existing strategy-governance lifecycle to take effect.

The engine also fails closed on empty observations, mixed strategy versions, invalid metrics, and insufficient samples.

## Inputs

Each observation identifies one immutable strategy version and records:

- realized return;
- maximum drawdown;
- win rate;
- trade count;
- observation timestamp.

Multiple observations may be aggregated only when they refer to the same strategy version.

## Next integration

Later stages can persist these assessments beside strategy/performance evidence, feed drift alerts into operations, and generate replacement research candidates. Any replacement must become a new immutable strategy version and pass the existing validation and promotion gates.
