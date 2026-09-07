# Autonomous Stage H — Implementation Notes

Stage H introduces deterministic performance observation and drift assessment for immutable strategy versions.

The engine evaluates realized return, drawdown, win rate, and trade sample size. It emits `continue`, `review`, or `retire_candidate` without changing strategy state.

A `retire_candidate` is an observation for the existing governance lifecycle, not an automatic retirement or promotion. Active strategy versions remain immutable.
