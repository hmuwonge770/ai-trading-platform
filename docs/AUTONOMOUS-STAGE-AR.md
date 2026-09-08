# Stage AR — Production Soak & Evidence

## Objective

Evaluate bounded production-canary evidence for soak completion without turning the evaluation layer into an execution mechanism.

## Five implementation phases

1. **Soak contract & evidence model** — immutable policy/evidence records with timezone-aware windows and deterministic SHA-256 evidence integrity.
2. **Soak evaluator** — deterministic COMPLETE/HOLD/ABORT decisions against duration, sample, freshness, error, reconciliation, drawdown, slippage, and continuity boundaries.
3. **Evidence integration** — compose canary completion and upstream promotion/risk/capital/runtime/kill-switch gates without mutating their state.
4. **Safety verification** — identity mismatch, digest tampering, stale/invalid evidence, threshold failures, concurrency/determinism, and kill-switch tests.
5. **CI and release verification** — branch CI, pull-request review, merge, post-merge CI, and roadmap verification.

## Safety invariants

- Evidence is immutable and strategy/canary identity-bound.
- Evidence digests are deterministic SHA-256 values over a canonical representation.
- NaN, infinity, negative counts, naive timestamps, and inverted time windows fail closed.
- Stale or tampered evidence cannot complete the soak.
- Any upstream governance, runtime, or kill-switch failure prevents completion.
- AR cannot widen capital, risk, cohort, or runtime limits.
- AR cannot accept exchange credentials or submit exchange orders.
- AR does not activate live execution or mutate runtime, authorization, promotion, risk, capital, or kill-switch state.
- Repeated evaluation of identical evidence is deterministic and read-only.

## Completion meaning

`COMPLETE` means the supplied evidence satisfies the approved soak policy. It does **not** mean an exchange order should be submitted, a runtime should be enabled, or production capital should be increased.
