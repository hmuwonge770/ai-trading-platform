# Stage AG — Position Recovery

## Objective
Provide deterministic, fail-closed recovery assessment for autonomous position state after execution uncertainty, restart, or exchange-state divergence.

## Five implementation phases
1. **Design & contract** — define expected/observed position contracts and explicit recovery outcomes.
2. **Core implementation** — compare position identity and quantity using a bounded tolerance and freshness window.
3. **Safety/control integration** — route missing, orphaned, mismatched, stale, or invalid state to HALT; no trading authority is introduced.
4. **Tests & failure scenarios** — cover matching, missing, orphaned, quantity mismatch, stale/future snapshots, and invalid inputs.
5. **CI → merge → post-merge verification** — require branch CI, merge to `main`, and successful post-merge CI before advancing.

## Safety boundary
This stage is deliberately read-only. It does not submit, cancel, amend, or retry orders; allocate capital; change risk limits; authorize live trading; or access exchange credentials. Unsafe position state is never silently adopted. Recovery requires reconciliation and remains subject to the existing risk, execution, authorization, and runtime boundaries.

## Recovery semantics
- `MATCHED` → `CONTINUE`
- `MISSING`, `ORPHANED`, `QUANTITY_MISMATCH`, `STALE`, `UNAVAILABLE` → `HALT`
- Snapshot timestamps must be valid and within the configured freshness window.
- Position quantities must match within the configured tolerance.
