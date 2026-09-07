# Stage AE — Exchange Connectivity Resilience

## Objective

Provide a credential-free, deterministic exchange reachability monitor so autonomous runtime components can fail closed when connectivity becomes unreliable.

## Five implementation phases

1. **Design & contract** — explicit connectivity states, immutable policy/report contracts, and an application-owned probe protocol.
2. **Core implementation** — consecutive-failure and consecutive-success hysteresis.
3. **Safety/control integration** — degraded/offline connectivity is observable to the control plane without granting order authority.
4. **Tests & failure scenarios** — transport exceptions, repeated failures, recovery, counter reset, invalid policy, and no implicit retries.
5. **CI → merge → post-merge verification** — lint/tests, merge after green CI, and verify the resulting main-branch workflow.

## State semantics

- `ONLINE`: connectivity has met the configured recovery threshold.
- `DEGRADED`: connectivity has failed but has not yet crossed the offline threshold.
- `OFFLINE`: repeated failures have crossed the configured offline threshold.

The monitor starts `OFFLINE` by default and requires consecutive successful probes before declaring the exchange reachable.

## Critical safety decision

This stage deliberately **does not automatically retry order submissions**. Retrying an uncertain order request can create duplicate orders when the exchange accepted the original request but the response was lost. Order-specific recovery belongs to Stage AF and must be driven by client-order identity and reconciliation.

Connectivity checks are single-attempt observations. Probe exceptions are treated as failed connectivity. The monitor has no exchange credentials and cannot submit, cancel, amend, authorize, promote, allocate capital, or modify risk policy.

## Default thresholds

- degrade after 1 failed probe;
- go offline after 3 consecutive failed probes;
- return online after 2 consecutive successful probes.
