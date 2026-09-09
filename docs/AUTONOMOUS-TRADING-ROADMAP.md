# Autonomous AI Trading Roadmap

This roadmap defines the autonomous-trading track for the AI Trading Platform.

## Objective

Evolve the platform from AI-assisted research with human live authorization into an autonomous trading system that continuously observes markets, evaluates strategies, makes trading decisions, executes within deterministic risk limits, reconciles state, and adapts strategy under controlled governance.

Autonomy does not mean allowing an LLM to issue arbitrary exchange commands. The AI decision plane remains constrained by typed strategy specifications, deterministic risk controls, execution policy, state validation, circuit breakers, and an immutable audit trail.

## Lifecycle

```text
Market Data -> Feature/Regime Detection -> AI Research Loop -> Candidate Strategy Evaluation
-> Strategy Selection -> Autonomous Signal Decision -> Deterministic Risk Gate
-> Authorization / Policy Gates -> Autonomous Execution -> Exchange Events
-> Reconciliation -> Accounting / Portfolio State -> Performance / Drift Evaluation
-> Learning / Strategy Review -> Strategy Promotion or Retirement
-> Monitoring / Alerting -> Recovery / Incident Handling -> repeat
```

## Stages

### Foundation — A–J
- **A** — Autonomous Trading Control Plane
- **B** — Continuous Market Intelligence
- **C** — AI Decision Engine
- **D** — Autonomous Risk Engine
- **E** — Autonomous Execution Loop
- **F** — Position & Portfolio Agent
- **G** — Continuous Strategy Learning
- **H** — Autonomous Promotion
- **I** — Autonomous Reliability & Recovery
- **J** — Production Autonomous Mode

### Controlled Testnet — K–O
- **K** — Binance Testnet Execution
- **L** — Testnet Autonomous Runner
- **M** — Testnet Reconciliation & State Recovery
- **N** — Testnet Accounting Integrity
- **O** — Testnet Performance Attribution

### Promotion & Authorization — P–T
- **P** — Promotion Readiness
- **Q** — Promotion Evidence Handoff
- **R** — Live Authorization Preflight
- **S** — Authorization Freshness & Expiry
- **T** — Authorization Consumption Guard

### Live Execution Foundation — U–Y
- **U** — Live Execution Boundary
- **V** — Credential-Isolated Adapter Preflight
- **W** — Credential-Isolated Live Adapter
- **X** — Live Runtime Controls
- **Y** — Live Runtime Orchestration

### Observability & Operations — Z–AB
- **Z** — Execution Observability & Audit Trail
- **AA** — Execution Monitoring & Alerting
- **AB** — Operational Alert Delivery

### Production Hardening — AC–AY
- **AC** — Durable Alert & Incident Lifecycle
- **AD** — Autonomous Health State Machine
- **AE** — Exchange Connectivity Resilience
- **AF** — Order Lifecycle Recovery
- **AG** — Position Recovery
- **AH** — Persistent Autonomous State
- **AI** — Multi-Instance Safety
- **AJ** — Disaster Recovery
- **AK** — Strategy Lifecycle Automation
- **AL** — Automated Strategy Evaluation
- **AM** — Strategy Retirement Automation
- **AN** — Capital Allocation Governance
- **AO** — Risk Policy Governance
- **AP** — Autonomous Promotion Governance
- **AQ** — Production Canary
- **AR** — Production Soak & Evidence
- **AS** — Autonomous Incident Response
- **AT** — Operational SLOs & Capacity
- **AU** — Security Hardening
- **AV** — End-to-End Failure Testing
- **AW** — Production Readiness Review
- **AX** — Controlled Production Expansion
- **AY** — Full Autonomous Lifecycle Validation

### Completion — AZ

**Stage AZ — Fully Autonomous Production Operation** is the final completion milestone. The platform must operate the complete bounded autonomous lifecycle continuously in production while retaining deterministic controls and immutable governance.

AZ requires continuous market intelligence and decisions, deterministic risk gating, explicit live authorization/runtime gates, credential isolation, reconciliation of exchange/order/position/accounting/strategy state, continuous performance and drift evaluation, deterministic quarantine/retirement, immutable capital/risk ceilings, continuous monitoring/alerting/incident handling/recovery, durable restart-safe state, multi-instance idempotency, disaster recovery, failure testing, production canary/soak evidence, SLO/security evidence, and end-to-end lifecycle validation.

AZ does not mean unrestricted autonomy. AI cannot bypass risk, disable safety controls, obtain raw exchange credentials, arbitrarily modify executable code, or change capital/risk ceilings. The system remains fail closed, auditable, and subject to hard global shutdown controls.

## Current implementation status

- **AN — Capital Allocation Governance:** merged to `main`.
- **AO — Risk Policy Governance:** merged to `main`; post-merge CI verified green.
- **AP — Autonomous Promotion Governance:** merged to `main`; post-merge CI verified green.
- **AQ — Production Canary:** merged to `main`; post-merge CI verified green.
- **AR — Production Soak & Evidence:** merged to `main`; post-merge CI verified green.
- **AS — Autonomous Incident Response:** merged to `main`; post-merge CI verified green.
- **AT — Operational SLOs & Capacity:** merged to `main`; post-merge CI verified green.
- **AU — Security Hardening:** merged to `main`; post-merge CI verified green.
- **AV — End-to-End Failure Testing:** merged to `main`; merge commit `190161420ef60682f60099cc8689353f88ec17ac`; post-merge CI run `34326490542` verified green.
- **AW — Production Readiness Review:** merged to `main`; merge commit `3031614c3b5fdc1fef7092ca9e42fddd58cd4b25`; post-merge CI run `34327141323` verified green.
- **Next:** AX — Controlled Production Expansion.

## Stage AT implementation phases

1. Immutable SLO policy contract.
2. Validated operational observation model.
3. Deterministic SLO and capacity evaluator.
4. Safety-gated governance integration.
5. Boundary, failure, determinism and regression coverage.
6. Documentation, CI, merge and post-merge verification.

## Stage AU implementation phases

1. Security contract and immutable policy.
2. Deterministic security assessment.
3. Governance integration and strategy identity binding.
4. Failure, boundary and determinism coverage.
5. Package exports and documentation.

## Stage AV implementation phases

1. Failure contract and bounded response policy.
2. Deterministic failure assessment.
3. Governance integration and strategy identity binding.
4. Boundary, failure and determinism coverage.
5. Package exports and documentation.
6. CI, merge and post-merge verification.

## Stage AW implementation phases

1. Immutable production-readiness policy and observation contract.
2. Deterministic readiness evaluator.
3. Governance integration and strategy identity binding.
4. Boundary, failure and determinism coverage.
5. Package exports and documentation.
6. CI, merge, post-merge verification and roadmap advancement.

## Completion rule

Each stage must be implemented, tested, pass CI, merged to `main`, and have post-merge CI verified before the next stage is treated as complete. Live capability is never inferred merely because a code path exists; runtime configuration, authorization, policy, and operational evidence remain mandatory.

## Non-negotiable boundaries

- AI never receives raw Binance API secrets.
- AI never directly calls Binance.
- AI cannot override risk decisions.
- AI cannot disable the kill switch or circuit breaker.
- AI cannot increase capital limits on its own.
- AI cannot mutate an active immutable strategy version.
- Unknown exchange state is reconciled before dependent actions continue.
- Stale market data or stale AI decisions fail closed.
- Autonomous mode has a hard global disable control.
