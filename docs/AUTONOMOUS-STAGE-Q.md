# Autonomous Stage Q — Promotion Workflow Evidence Handoff

## Objective

Stage Q connects the deterministic Stage P readiness evidence to the existing promotion workflow as an immutable handoff. It does not create promotions or grant authorization.

## Behavior

- Healthy non-live readiness produces `READY_FOR_NON_LIVE_WORKFLOW`.
- Healthy evidence targeting a live stage produces `HUMAN_REVIEW_REQUIRED`.
- Unhealthy or incomplete evidence remains `BLOCKED`.
- The handoff contains a deterministic SHA-256 evidence hash and the strategy fingerprint.
- Strategy/report/evidence identity mismatches fail closed.

## Safety boundaries

- No Binance client or credentials.
- No order submission, cancellation, amendment, or repair.
- No capital allocation or capital-limit changes.
- No automatic approval or activation of live promotions.
- Existing promotion approvals remain authoritative.
- Live stages always require the existing human authorization workflow.

The integration is intentionally a handoff/reporting layer. A `HUMAN_REVIEW_REQUIRED` result is not an authorization to trade.

## Next stage

The next stage can consume the immutable evidence binding inside the promotion persistence/audit workflow while keeping approval and activation explicitly human-controlled.
