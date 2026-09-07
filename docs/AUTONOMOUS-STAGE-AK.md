# Autonomous Stage AK — Strategy Lifecycle Automation

## Objective

Automate bounded strategy lifecycle transitions from deterministic learning evidence without allowing the AI to bypass governance or grant live trading authority.

### Phase 1 — Design & contract

Define explicit states: `DRAFT`, `CANDIDATE`, `ACTIVE`, `QUARANTINED`, and `RETIRED`. Lifecycle decisions are immutable reports and are keyed to the exact strategy version ID.

### Phase 2 — Core implementation

`AutonomousStrategyLifecycle` consumes the existing deterministic `DriftAssessment` and produces a bounded lifecycle report. Retirement candidates become retired; active strategies requiring review become quarantined.

### Phase 3 — Safety/control integration

Candidate activation is disabled by default. A quarantined strategy cannot self-reactivate. Strategy identity mismatches fail closed. Lifecycle automation has no exchange, credential, capital, authorization, or risk-policy authority.

### Phase 4 — Tests & failure scenarios

Tests cover review quarantine, deterministic retirement, blocked candidate activation, blocked quarantine reactivation, strategy identity mismatch, and retired-state immutability.

### Phase 5 — CI → merge → post-merge verification

Run lint and the complete test suite, merge only after CI is green, then verify the post-merge `main` workflow before treating AK as complete.

## Safety invariants

- Learning evidence is deterministic input; lifecycle automation cannot rewrite it.
- Live authorization is never created or consumed here.
- Capital and risk ceilings cannot be changed here.
- A quarantined strategy cannot autonomously return to active execution.
- Retirement is terminal in this component.
- No Binance credentials or exchange client is accessed.
