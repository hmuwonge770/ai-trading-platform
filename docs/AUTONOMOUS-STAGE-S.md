# Autonomous Trading — Stage S

## Authorization Freshness & Expiry Enforcement

Stage S adds a deterministic, read-only guard that validates an existing live authorization snapshot immediately before it can be consumed by an execution authorization path.

### Checks

The guard fails closed unless all of the following remain true:

- the promotion identity matches the authorization snapshot;
- the promotion is still explicitly `APPROVED`;
- the authorization targets a live promotion stage;
- the execution environment matches the authorized environment;
- the strategy version and immutable strategy fingerprint match;
- the risk-policy fingerprint matches;
- the evidence snapshot hash matches;
- the authorization hash is structurally valid; and
- the current UTC time is strictly before `expires_at`.

An expired authorization is reported as `EXPIRED`; integrity or state mismatches are reported as `BLOCKED`.

### Safety properties

- No approval is created or changed.
- Expiry is never extended automatically.
- Promotions are never activated or mutated.
- No Binance client or credential is owned by this module.
- No orders are submitted, cancelled, amended, or repaired.
- Existing risk, kill-switch, circuit-breaker, reconciliation, accounting, and human-authorization controls remain mandatory.
- A stale or expired authorization cannot silently fall back to an older approval.

The guard is intended to be invoked at the final authorization boundary, after the existing live preflight and before any future live execution submitter is allowed to act.

## Tests

Unit coverage verifies healthy authorization, expiry, promotion-state mismatch, environment mismatch, strategy identity/fingerprint mismatch, risk-policy mismatch, evidence mismatch, and timezone-aware time requirements.

## Default posture

This stage does not enable live trading. The system remains fail closed unless the existing explicit authorization and execution controls are satisfied.
