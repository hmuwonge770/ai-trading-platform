# Stage 18 — Accounting & Transactions

Stage 18 establishes the accounting boundary for portfolio and execution events.

## Invariants

- Transactions are immutable once created.
- Every transaction contains at least two entries.
- Each entry is exactly one debit or one credit and cannot be negative.
- Transactions must balance independently for every asset.
- The domain ledger is idempotent by transaction reference.
- Accounting is deterministic and does not submit exchange orders.

## Persistence

PostgreSQL stores an append-only transaction header and ordered journal entries.
The transaction reference is unique, while entries have a unique line number per
transaction. Database constraints prevent negative values and entries that have
both debit and credit sides populated.

## Scope boundary

Stage 18 records accounting facts; it does not yet make execution persistence,
outbox delivery, reconciliation, or live authorization decisions. Those remain
later reliability and promotion stages.
