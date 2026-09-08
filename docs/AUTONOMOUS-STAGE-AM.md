# Autonomous Stage AM — Strategy Retirement Automation

## Objective

Automate deterministic strategy-retirement decisions from the Stage AL evaluation result while keeping lifecycle mutation and live execution authority bounded and auditable.

### Phase 1 — Design & contract

Define immutable retirement decisions (`RETIRE`, `HOLD`, `BLOCK`) keyed to the exact strategy version ID. Retirement is permitted only from explicit Stage AL rejection evidence whose action is `RETIRE_CANDIDATE`.

### Phase 2 — Core implementation

`AutonomousStrategyRetirement` consumes a `StrategyEvaluationReport` and current `StrategyLifecycleState`. It produces a bounded retirement report without changing lifecycle state itself. A retired strategy is idempotent; review/quarantine evidence never becomes retirement; identity mismatches are blocked.

### Phase 3 — Safety/control integration

Retirement automation cannot activate strategies, submit orders, alter capital/risk ceilings, access Binance credentials, or directly mutate exchange state. It only produces a deterministic lifecycle decision for a separate lifecycle/state-writer boundary.

### Phase 4 — Tests & failure scenarios

Tests cover valid active retirement, candidate retirement, already-retired idempotency, review/hold, accepted/continue hold, identity mismatch, invalid strategy identity, and non-retirement rejection evidence.

### Phase 5 — CI → merge → post-merge verification

Run lint and the complete test suite, merge only after CI is green, then verify the post-merge `main` workflow before treating AM as complete.

## Safety invariants

- Retirement evidence is immutable input.
- Strategy identity must match exactly.
- Only explicit `REJECT + RETIRE_CANDIDATE` evidence can produce `RETIRE`.
- Review and quarantine never silently become retirement.
- Retirement planning is separate from lifecycle state mutation.
- No Binance credentials or exchange client is accessed.
- No capital or risk ceiling can be changed.
