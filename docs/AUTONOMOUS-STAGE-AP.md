# Autonomous Stage AP — Promotion Governance

Stage AP adds the deterministic governance boundary that decides whether an already-evaluated strategy may proceed through a promotion stage. It consumes existing readiness evidence and the Stage AN/AO capital and risk boundaries; it does not create live authorization, execute exchange orders, or mutate governance state.

## Objective

Make autonomous promotion a bounded planning decision: a strategy may be promoted only when its immutable identity, lifecycle state, readiness evidence, risk boundary, and capital boundary all agree.

## Five-phase implementation plan

### Phase 1 — Promotion contract & immutable eligibility invariants
- Define typed promotion governance request/report/action contracts.
- Require an exact strategy-version identity match.
- Require readiness evidence to target the same promotion stage.
- Prevent retired and quarantined strategies from promotion.
- Keep promotion governance read-only: no lifecycle, strategy, policy, capital, authorization, or exchange mutation.

### Phase 2 — Deterministic promotion evaluator
- Produce `PROMOTE`, `HOLD`, or `BLOCK` deterministically.
- Ready evidence with valid identity and lifecycle state may promote.
- Review evidence holds for explicit review instead of bypassing governance.
- Blocked evidence, identity mismatch, and invalid stage relationships fail closed.
- Identical inputs produce identical reports.

### Phase 3 — Governance integration
- Compose promotion readiness with Stage AN capital allocation governance.
- Compose promotion with Stage AO risk policy governance boundaries.
- The tighter risk/capital boundary always wins.
- A promotion cannot authorize a notional that exceeds the approved order or capital capacity.
- Promotion governance remains separate from exchange execution and live authorization.

### Phase 4 — Failure, boundary & safety tests
- Cover strategy identity mismatch.
- Cover target-stage mismatch.
- Cover retired and quarantined strategies.
- Cover readiness review/block states.
- Cover risk and capital failures.
- Cover existing-exposure capacity reduction.
- Cover deterministic output and read-only policy behavior.

### Phase 5 — CI, merge & post-merge verification
- Run repository lint, Python tests, and dashboard tests.
- Merge only after branch CI is green.
- Verify the merged commit on `main`.
- Verify post-merge CI is green before marking AP complete.
- Update the autonomous roadmap only after post-merge verification.

## Safety boundaries

- No Binance credentials are accepted by this module.
- No exchange API is called.
- No order is submitted.
- No strategy definition or immutable version is modified.
- No capital ceiling or risk ceiling can be increased by promotion governance.
- Promotion governance does not create or consume live authorization.
- Retired or quarantined strategies cannot be promoted.
- Uncertain governance state fails closed.

## Completion gate

Stage AP is complete only after all five phases are implemented, CI passes, the changes are merged to `main`, post-merge CI is verified, and the roadmap status is updated.
