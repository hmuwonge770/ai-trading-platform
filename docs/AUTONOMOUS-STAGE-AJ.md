# Autonomous Stage AJ — Disaster Recovery

## Objective

Provide a deterministic, fail-closed recovery boundary for restarting autonomous operation after process, host, or service failure.

## Five implementation phases

1. **Design & contract** — define durable checkpoint/snapshot identity and recovery outcomes.
2. **Core implementation** — validate durable state freshness, integrity, and strategy identity.
3. **Safety/control integration** — recovery failure produces HALT and never grants trading authority.
4. **Tests & failure scenarios** — cover missing, stale, mismatched, future, and invalid state.
5. **CI → merge → post-merge verification** — require green branch CI, merge to `main`, then verify main CI.

## Safety invariants

- Recovery state must exist before autonomous continuation.
- Snapshot age is bounded.
- Checkpoint and snapshot version/digest must agree.
- Strategy fingerprint must match the requested runtime strategy.
- Future or malformed state fails closed.
- Recovery never submits, cancels, or amends orders.
- Recovery never changes capital limits, risk policy, authorization, or kill-switch state.
- Recovery is a prerequisite check, not an activation mechanism.
