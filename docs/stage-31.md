# Stage 31 — Two-Person Live Authorization

Stage 31 converts a `LIVE_ELIGIBLE` readiness result into an immutable human authorization record. Readiness alone never grants live trading access.

## Required approvals

Exactly one approval from each required role is needed:

- Risk Manager
- Admin

The two approvals must belong to distinct human identities. The requester cannot approve their own authorization.

## Frozen authorization boundary

The authorization binds the exact:

- strategy version ID
- strategy SHA-256 fingerprint
- risk-policy fingerprint
- capital allocation
- position/loss/order limits
- production-readiness evidence hash
- approval identities and roles
- authorization hash

Approval is rejected when a material value does not match the frozen authorization snapshot.

## Invalidation

Any material change creates a different authorization boundary. At minimum, changes to the strategy fingerprint, risk-policy fingerprint, capital allocation, strategy version, or readiness evidence invalidate the prior authorization.

The authorization hash is derived from the complete snapshot, so the execution boundary can compare the persisted authorization with the current values before allowing a live action.

## Safety boundary

Stage 31 does not submit exchange orders and does not grant Binance credentials. Execution remains responsible for final fail-closed preflight, risk checks, reconciliation health, kill-switch state, circuit-breaker state, endpoint isolation and credential selection.

## Verification

Unit tests cover:

- successful Risk Manager + Admin authorization;
- requester self-approval rejection;
- same-human dual-role rejection;
- missing required role rejection;
- readiness/strategy-version mismatch;
- strategy fingerprint invalidation; and
- capital allocation invalidation.
