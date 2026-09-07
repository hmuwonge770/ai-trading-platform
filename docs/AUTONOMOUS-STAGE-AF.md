# Stage AF — Order Lifecycle Recovery

## Objective

Recover ambiguous autonomous orders without blindly resubmitting requests that may already have been accepted by the exchange.

## Five implementation phases

1. **Design & contract** — explicit order lifecycle states, recovery events, bounded resubmission policy, and immutable reports.
2. **Core implementation** — deterministic lifecycle transitions and terminal-state handling.
3. **Safety/control integration** — response loss and query failure become `UNKNOWN` and require reconciliation before any retry decision.
4. **Tests & failure scenarios** — lost responses, failed queries, confirmed absence, partial fills, terminal states, and retry-budget exhaustion.
5. **CI → merge → post-merge verification** — lint/tests, merge only after green CI, then verify main-branch CI.

## Recovery rules

- `RESPONSE_LOST` or `QUERY_FAILED` → `UNKNOWN` + `RECONCILE`.
- `CONFIRMED_NOT_FOUND` can authorize a bounded resubmission only when the order is already `UNKNOWN`.
- Resubmissions are limited by an explicit budget and then fail closed to `HALT`.
- `FILLED`, `CANCELED`, and `REJECTED` are terminal and cannot be reopened by a later recovery event.

## Safety boundary

The recovery state machine does not perform exchange calls and has no credentials. It produces a decision for an application-owned execution/reconciliation layer. It cannot bypass risk, authorization, capital limits, the kill switch, or promotion gates.

The design intentionally avoids generic automatic retries of uncertain order requests because a lost response does not prove that the exchange rejected the order. Positive exchange state confirmation and client-order identity are required before resubmission.

## Default policy

At most one resubmission is permitted for an explicitly confirmed absent order. Applications may configure a lower budget, including zero.
