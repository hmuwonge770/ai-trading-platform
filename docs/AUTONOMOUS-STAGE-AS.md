# Stage AS — Autonomous Incident Response

## Objective

Provide a deterministic control-plane layer that detects operational incidents, classifies severity, selects bounded containment/escalation/abort actions, and preserves restart-safe decision identity.

## Implementation phases

1. **Incident contract & severity model** — typed immutable observations, actions, policies, and fail-closed validation.
2. **Deterministic incident detection & classification** — normalize upstream health facts into stable incident signals and severity.
3. **Response planning & governance integration** — compose detection with bounded response decisions while preserving runtime, authorization, reconciliation, accounting, and kill-switch boundaries.
4. **Recovery, escalation & idempotency** — enforce recovery-attempt limits and persist/replay decisions by incident fingerprint without duplicate authority.
5. **Failure, boundary, concurrency & safety testing** — validate critical failures, repeated incidents, invalid identities/counters, kill-switch behavior, immutability, and deterministic replay.
6. **CI, merge & post-merge verification** — lint/tests, PR review, merge, post-merge CI, and roadmap evidence.

## Safety invariants

- No Binance credentials are accepted or exposed.
- No exchange order is submitted by AS.
- Incident response cannot widen capital or risk limits.
- Incident response cannot disable the global kill switch.
- Invalid identity, evidence, or counters fail closed.
- Authorization, adapter, reconciliation, and accounting failures are critical.
- Repeated incidents escalate rather than silently retry forever.
- Recovery attempts are bounded.
- Decisions are immutable and idempotent by fingerprint.
- The response layer is planning/governance only; application-owned executors remain responsible for any separately authorized operational action.
- Identical inputs produce identical decisions.

## Response semantics

`NO_ACTION` means no operational containment is warranted.

`CONTAIN` means the application may invoke an independently authorized containment mechanism; AS itself performs no mutation.

`ESCALATE` means the incident requires higher-level operational handling.

`ABORT` is fail-closed and indicates that autonomous activity must remain stopped pending recovery or human/operator handling.
