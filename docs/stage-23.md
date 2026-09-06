# Stage 23 — PostgreSQL Promotion Repository

Stage 23 replaces process-local promotion persistence with a PostgreSQL repository boundary.

## Guarantees

- Promotions and capital allocations are persisted transactionally.
- Approval uses a PostgreSQL `FOR UPDATE` lock on the promotion row.
- Activation locks both the promotion and approval rows before checking the required independent Risk Manager and Admin approvals.
- Approval uniqueness is enforced by `(promotion_id, approver_id)`.
- Authorization snapshots are persisted with their strategy, evidence and risk-policy fingerprints.
- Monetary limits use PostgreSQL `NUMERIC`, not floating point.
- The repository contains no exchange client, credentials, or order-submission path.

The repository is intentionally below the deterministic promotion domain and does not grant itself live trading authority. Existing environment and preflight guards remain separate execution boundaries.
