# Stage AN — Capital Allocation Governance

Stage AN governs autonomous capital allocation without allowing strategy logic or AI decisions to increase approved capital ceilings.

## Five-phase implementation

### Phase 1 — Allocation contract & invariants
Define typed allocation inputs/outputs and fail-closed invariants.

### Phase 2 — Deterministic allocation engine
Implement bounded allocation planning from approved capital, strategy demand, and existing exposure.

### Phase 3 — Risk/capital boundary integration
Ensure allocation cannot exceed immutable ceilings or bypass deterministic risk gates.

### Phase 4 — Failure, concurrency & safety tests
Cover invalid inputs, ceiling exhaustion, duplicate strategy identities, over-allocation, and deterministic repeatability.

### Phase 5 — CI, merge & post-merge verification
Run lint/tests and dashboard checks, merge only after green CI, then verify the merged main commit and post-merge checks.

## Non-negotiable invariants

- Capital ceilings are externally approved and immutable to autonomous strategy logic.
- Allocation planning never increases the configured portfolio capital ceiling.
- A strategy cannot receive more than its approved per-strategy ceiling.
- Existing exposure is deducted before additional allocation is planned.
- Invalid, negative, NaN, or infinite monetary inputs fail closed.
- Allocation is deterministic for identical inputs.
- Strategy identity mismatches block allocation.
- Allocation planning does not place exchange orders or access Binance credentials.
- Allocation planning does not mutate capital ceilings, risk policies, or strategy definitions.
- Zero available capacity produces a safe zero-allocation result rather than an exception or implicit override.
