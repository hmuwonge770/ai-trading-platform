# Stage AZ — Fully Autonomous Production Operation

Stage AZ is the final roadmap milestone. It composes the previously verified autonomous control-plane stages into continuous bounded production operation.

## Safety boundary

AZ is not unrestricted AI autonomy. The AI decision plane never receives raw Binance credentials, never calls Binance directly, cannot override deterministic risk controls, cannot disable the global kill switch, cannot increase capital or risk ceilings, and cannot mutate immutable strategy versions. Unknown exchange state, stale evidence, failed reconciliation, failed security controls, or missing authorization fail closed.

## Implementation phases

1. **Immutable production-operation contract** — define typed observations, hard ceilings, required gates, strategy identity, and deterministic fail-closed behavior.
2. **Continuous lifecycle evaluator** — compose market/decision readiness, risk, authorization, runtime, reconciliation, accounting, monitoring, learning, promotion, retirement, and recovery evidence into one deterministic operation decision.
3. **Cross-stage governance integration** — require AW readiness, AX expansion bounds, AY lifecycle validation, security, incident, SLO, canary, soak, failure-testing, capital and risk evidence without bypassing upstream controls.
4. **Restart-safe durable operation state** — bind operation decisions to strategy identity and durable revisions, provide idempotent replay, and prevent duplicate work across instances or restarts.
5. **Continuous safety enforcement** — enforce global shutdown, stale-data/decision blocking, reconciliation-first behavior, incident containment, SLO/security failures, and deterministic halt semantics.
6. **End-to-end production verification** — add failure/concurrency/replay tests, documentation, package exports, CI, merge, post-merge CI, roadmap completion, and roadmap-update CI verification.

## Completion criteria

AZ is complete only when the complete bounded lifecycle is continuously governable in production, all hard controls remain externally authoritative, state is restart-safe and multi-instance safe, and the implementation plus post-merge verification is green.

A code path that exists is not evidence that live execution is enabled. Runtime mode, authorization, adapter preflight, capital/risk policy, kill switch, and operational evidence remain mandatory.
