# Autonomous Stage AL — Automated Strategy Evaluation

## Objective

Evaluate strategy versions deterministically from existing learning evidence while keeping lifecycle governance and live execution authority separate.

### Phase 1 — Design & contract

Define immutable evaluation status (`ACCEPT`, `REVIEW`, `REJECT`) and bounded actions (`CONTINUE`, `QUARANTINE`, `RETIRE_CANDIDATE`). Evaluation is keyed to the exact strategy version ID supplied by the learning engine.

### Phase 2 — Core implementation

`AutonomousStrategyEvaluator` consumes `DriftAssessment` and applies explicit minimum score and sample-size gates. Retirement candidates are rejected, review evidence is quarantined, and sufficiently supported continuation evidence is accepted.

### Phase 3 — Safety/control integration

Evaluation cannot activate a strategy, create authorization, alter capital/risk ceilings, submit orders, or access credentials. Insufficient evidence is never treated as approval.

### Phase 4 — Tests & failure scenarios

Tests cover acceptance, review/quarantine, retirement rejection, insufficient samples, low scores, and invalid strategy identity.

### Phase 5 — CI → merge → post-merge verification

Run lint and the complete test suite, merge only after CI is green, then verify the post-merge `main` workflow before treating AL as complete.

## Safety invariants

- Learning evidence remains immutable input.
- Evaluation is deterministic and bounded.
- Review never silently becomes approval.
- Rejection cannot directly mutate lifecycle state.
- No Binance credentials or exchange client is accessed.
