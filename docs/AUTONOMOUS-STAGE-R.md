# Autonomous Stage R — Live Authorization Preflight

## Objective

Stage R adds a deterministic, read-only preflight between autonomous evidence
handoff and the existing human-controlled live authorization workflow.

## Behavior

The preflight verifies:

- the promotion is still pending;
- the target is a supported live stage;
- the Stage Q evidence handoff explicitly requires human review;
- strategy version and immutable fingerprint match;
- target stage matches the promotion;
- the evidence hash is structurally valid;
- any existing approval uses the same evidence hash.

A successful result means **ready for human authorization**, not approved or
active.

## Safety boundaries

- no Binance client or credentials;
- no order submission, cancellation, amendment, or repair;
- no capital allocation changes;
- no approval creation or approval mutation;
- no promotion activation;
- no bypass of the Risk Manager/Admin authorization requirements;
- immutable strategy identity remains authoritative.

A failed preflight is fail-closed and returns explicit reasons for review.

## Next stage

The next stage should strengthen authorization freshness and expiry checks
before any live execution path consumes an authorization snapshot.
