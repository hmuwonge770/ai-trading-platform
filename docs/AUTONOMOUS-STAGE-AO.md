# Stage AO — Risk Policy Governance

## Objective

Add an explicit, deterministic governance boundary for autonomous risk policy. The stage makes externally approved risk limits authoritative and prevents strategy logic from weakening, escalating, or mutating those limits.

## Five phases

1. **Risk-policy contract & invariants** — typed immutable policy and fail-closed validation.
2. **Deterministic policy evaluator** — evaluate proposed exposure against approved limits.
3. **Governance integration** — compose AO with the existing autonomous risk boundary and Stage AN capital allocation without granting new execution authority.
4. **Failure & safety testing** — invalid, stale, non-finite, boundary, identity, and policy-conflict cases.
5. **CI → merge → post-merge verification** — green CI, merge to `main`, and verify post-merge CI.

## Dependency sequencing

Stage AN is the prerequisite capital-allocation governance boundary. It must be present on `main` before AO is validated or merged. AO does not duplicate or copy Stage AN implementation; it consumes the merged AN contract as its lower-level capacity boundary.

## Non-negotiable invariants

- Approved risk limits are external inputs and immutable during evaluation.
- Autonomous strategy logic cannot increase a risk limit.
- A tighter policy bound always wins.
- Existing exposure is included when calculating remaining capacity.
- Missing, invalid, negative, NaN, or infinite values fail closed.
- Identical inputs produce identical governance results.
- Strategy identity is required and cannot be silently substituted.
- The governance layer does not place exchange orders or access Binance credentials.
- The governance layer does not mutate capital ceilings, risk policies, strategy definitions, or runtime authorization.

## Phase 1 gate

The contract is represented by immutable dataclasses and centralized finite/non-negative validation.

## Phase 2 gate

The evaluator returns a deterministic allow/deny decision and never modifies the supplied policy.

## Phase 3 gate

The governance adapter can tighten the existing autonomous risk policy but cannot widen it. Stage AN capital allocation remains a separate lower-level capacity boundary.

## Phase 4 gate

Tests cover policy validation, tighter bounds, exposure, identity, determinism, and fail-closed behavior.

## Phase 5 gate

CI must pass against the current `main`, including the merged Stage AN dependency, before merge. After merge, `main` and its workflow must be independently verified before Stage AO is considered complete.
