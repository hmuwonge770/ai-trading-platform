# Autonomous Stage AQ — Production Canary

## Objective

Add a bounded production-canary governance layer that can deterministically decide whether a strategy is eligible for a small production cohort. AQ is a control-plane decision layer, not an autonomous live-trading switch.

## Five implementation phases

### Phase 1 — Canary contract and immutable safety invariants

- Define immutable canary policy, request, action, and report contracts.
- Require an explicit operator approval signal.
- Bound cohort size by an externally approved maximum.
- Reject negative, non-finite, or invalid values.
- Never mutate promotion, authorization, runtime, risk, or capital state.

### Phase 2 — Deterministic eligibility and rollout evaluator

- Require promotion, risk, capital, runtime, and kill-switch gates.
- Require sufficient evidence before starting.
- Enforce error-rate, reconciliation, drawdown, and slippage ceilings.
- Use deterministic strategy identity hashing for cohort assignment.
- Produce START, HOLD, or ABORT without executing a trade.

### Phase 3 — Runtime and governance integration

- Compose AQ with upstream governance decisions.
- Treat the deployment kill switch as an absolute boundary.
- Never enable `LiveRuntimeMode.ENABLED` or execution merely because AQ returns START.
- Never widen risk or capital ceilings.

### Phase 4 — Failure, boundary, concurrency, and safety tests

- Cover every upstream gate and every operational threshold.
- Cover deterministic cohort assignment and repeated evaluation.
- Cover invalid/non-finite inputs and policy immutability.
- Verify no exchange-order or credential path is introduced.

### Phase 5 — CI, merge, and post-merge verification

- Run lint, Python tests, and dashboard tests.
- Require green branch CI before PR merge.
- Merge only the verified AQ head SHA.
- Verify main points to the merge commit and post-merge CI is green.
- Only after post-merge verification, update the roadmap to mark AQ complete and advance to AR.

## Safety invariants

1. AQ cannot enlarge any risk or capital boundary.
2. AQ cannot bypass promotion or authorization governance.
3. AQ cannot clear or override the deployment kill switch.
4. AQ cannot enable live execution or submit exchange orders.
5. AQ does not accept or persist Binance credentials.
6. Immutable policies and reports prevent in-process mutation.
7. Invalid operational measurements fail closed.
8. Identical inputs produce identical decisions.
9. A canary decision is advisory/control-plane output; activation remains outside AQ.
