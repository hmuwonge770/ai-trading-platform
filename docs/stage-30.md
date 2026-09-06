# Stage 30 — Production Readiness

Stage 30 introduces a deterministic, fail-closed production-readiness gate.

## Required evidence

A strategy version must provide passing evidence for every gate:

- research
- paper
- testnet
- security
- failure
- reconciliation
- backup/restore
- observability
- 72-hour soak
- Kubernetes isolation

Missing evidence or failed evidence means the strategy is **not** `LIVE_ELIGIBLE`.

## Important boundary

`LIVE_ELIGIBLE` is only a readiness state. It does **not**:

- arm live trading;
- activate a promotion;
- approve capital;
- bypass the risk gateway;
- grant exchange credentials; or
- submit an order.

Stage 31 remains responsible for independent human authorization. Any material change to the strategy, strategy fingerprint, risk policy, capital allocation, or authorization evidence must invalidate the subsequent authorization flow.

## Evidence model

Each readiness result contains an immutable strategy version/fingerprint and one unique evidence reference per required gate. Evidence is identified by an operator-controlled `evidence_id`; the readiness component does not fabricate test results.

The component deliberately does not claim that a backup, restore, soak, security assessment, or cluster deployment happened. Those systems must produce the evidence supplied to the gate.

## Fail-closed rule

The readiness report is eligible only when all required gates are present and passing. Duplicate gates, invalid strategy fingerprints, empty evidence identifiers, missing gates, or failed gates prevent eligibility.
