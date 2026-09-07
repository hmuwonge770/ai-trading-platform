# Autonomous Stage AH — Persistent Autonomous State

## Objective

Provide durable, restart-safe autonomous operational state without granting the persistence layer trading authority or storing exchange credentials.

## Five implementation phases

### Phase 1 — Design & contract

Define an immutable, versioned state snapshot and a persistence protocol. State is operational metadata only: lifecycle/mode, safety controls, strategy fingerprint, expected position symbols, pending client order IDs, revision, and capture time.

### Phase 2 — Core implementation

Implement in-memory and atomic JSON-file stores. File writes use a same-directory temporary file, restrictive permissions, `fsync`, and atomic replacement. Revisions must increase monotonically.

### Phase 3 — Safety/control integration

Add schema-version validation, freshness checks, corrupt/empty-state handling, and fail-closed restore semantics. A persisted kill switch or circuit breaker never becomes a reason to resume automatically.

### Phase 4 — Tests & failure scenarios

Cover serialization, immutability, secret-free payloads, revision conflicts, empty state, stale/future state, active safety controls, corrupt files, and file-store round trips.

### Phase 5 — CI → merge → post-merge verification

Run lint and the complete test suite in CI, merge only after green checks, then verify the resulting `main` commit's push workflow is green before treating AH as complete.

## Safety boundaries

- Persistence never contains Binance API secrets or credentials.
- Restoring state does not authorize live execution.
- Empty, stale, corrupt, schema-incompatible, or conflicting state fails closed.
- A kill switch or circuit breaker remains authoritative after restart.
- State revision numbers prevent silent rollback.
- The store has no order submission, cancellation, amendment, capital allocation, or risk-policy mutation authority.
- Applications must reconcile exchange state before resuming dependent actions after restart.

## Completion evidence

Stage AH is complete only after implementation, tests, CI, merge to `main`, and successful post-merge CI verification.
