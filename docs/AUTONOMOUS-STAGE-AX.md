# Stage AX — Controlled Production Expansion

## Purpose

AX provides a deterministic control-plane recommendation for expanding an already validated production canary. It permits only bounded, externally approved cohort growth.

## Implementation phases

1. **Expansion contract** — immutable ceiling, step-size, evidence and safety thresholds.
2. **Deterministic evaluator** — validates the requested delta and fails closed on invalid or unsafe observations.
3. **Governance integration** — composes canary, soak, promotion, risk, capital, runtime, kill-switch and operator gates.
4. **Idempotent decision ledger** — binds expansion decisions to strategy identity and request keys for restart/concurrency safety.
5. **Failure and boundary coverage** — verifies ceiling, step, evidence, kill-switch, runtime, capital and malformed-input behavior.
6. **Documentation and CI** — package exports, tests, branch CI, merge, post-merge CI and roadmap verification.

## Default boundaries

- Maximum production cohort: **5%**.
- Maximum expansion step: **1 percentage point**.
- Minimum soak evidence: **1,000 samples**.
- Maximum error rate: **1%**.
- Maximum drawdown: **2%**.
- Maximum slippage: **1%**.
- Maximum reconciliation failures: **0**.

These are governance defaults, not authority to increase capital or risk ceilings. External approved limits remain authoritative.

## Safety invariants

- AX never receives or handles raw Binance credentials.
- AX never submits exchange orders.
- AX never activates live runtime execution.
- AX never increases capital or risk ceilings.
- AX never disables the kill switch or bypasses authorization.
- Expansion requires completed canary and soak evidence plus every upstream governance gate.
- Missing critical gates fail closed.
- Non-finite, negative, regressive, over-step, or over-ceiling requests are rejected.
- Decisions are deterministic and strategy-identity bound.
- Repeated requests with the same identity and request key are idempotent.

## Operational meaning

`EXPAND` means **an approved bounded expansion may be considered by an external execution/control layer**. It does not itself change cohort membership, runtime configuration, capital allocation, risk policy, authorization, or exchange state.
