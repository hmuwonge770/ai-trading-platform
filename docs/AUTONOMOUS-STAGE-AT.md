# Stage AT — Operational SLOs & Capacity

## Objective

Provide a deterministic, read-only operational SLO and capacity governance layer for the autonomous trading control plane.

## Implementation phases

1. **SLO contract:** immutable availability, latency, error-rate, queue, worker, and capacity-headroom policy with finite-value validation.
2. **Observation model:** validated operational observations with bounded percentages and deterministic capacity utilization/headroom calculations.
3. **Governance evaluator:** deterministic HEALTHY / AT_RISK / BREACHED classification with explicit reasons and no state mutation.
4. **Safety integration:** compose SLO evidence with kill-switch and authorization context without enabling runtime or changing limits.
5. **Failure and boundary coverage:** threshold, invalid-value, short-window, concurrency, queue, headroom, determinism, and read-only tests.
6. **Documentation and CI:** document the operational contract, verify branch CI, merge, verify post-merge CI, then update the roadmap.

## Safety boundaries

- No Binance credentials are accepted or handled.
- No exchange orders are placed, cancelled, or modified.
- The evaluator cannot enable live runtime.
- Capital and risk ceilings are never changed.
- The kill switch remains authoritative.
- Invalid, non-finite, negative, or out-of-range observations fail closed at the contract boundary.
- SLO evaluation is deterministic and read-only.
- `HEALTHY` means the observed operational window satisfies AT thresholds; it is not authorization to trade.

## Default operational policy

- Availability >= 99%
- Decision latency <= 1000 ms
- Reconciliation latency <= 5000 ms
- Error rate <= 1%
- Queue depth <= 1000
- Active workers <= 32
- Capacity headroom >= 20%
- Observation window >= 300 seconds

## Non-goals

AT does not implement autoscaling, runtime activation, exchange execution, capital expansion, or autonomous infrastructure mutation. Those remain bounded operational concerns governed by later stages and hard external controls.
