# Autonomous AI Trading Roadmap

This branch is the autonomous-trading track for the AI Trading Platform.

## Objective

Evolve the platform from **AI-assisted research with human live authorization** into an **autonomous trading system** that can continuously observe markets, evaluate strategies, make trading decisions, execute within deterministic risk limits, reconcile state, and adapt its strategy under controlled governance.

Autonomy does **not** mean allowing an LLM to directly issue arbitrary exchange commands. The AI decision plane remains constrained by typed strategy specifications, deterministic risk controls, execution policy, state validation, circuit breakers, and an immutable audit trail.

## Autonomous lifecycle

```text
Market Data
  -> Feature/Regime Detection
  -> AI Research Loop
  -> Candidate Strategy Evaluation
  -> Strategy Selection
  -> Autonomous Signal Decision
  -> Deterministic Risk Gate
  -> Autonomous Execution
  -> Exchange Events
  -> Reconciliation
  -> Accounting / Portfolio State
  -> Performance / Drift Evaluation
  -> Learning / Strategy Review
  -> Strategy Promotion or Retirement
  -> repeat
```

## Development stages

### Autonomous Stage A — Autonomous Trading Control Plane

Introduce an explicit autonomous operating mode, decision-cycle state, policy boundaries, decision records, and kill-switch/circuit-breaker integration. Autonomous mode must default to disabled and fail closed.

### Autonomous Stage B — Continuous Market Intelligence

Build continuous market observation, feature generation, market-regime detection, data freshness checks, and signal context snapshots.

### Autonomous Stage C — AI Decision Engine

Allow the AI to select from approved strategy versions and produce typed trade decisions with confidence, rationale, evidence references, and expiry. The AI cannot create arbitrary executable trading code or bypass deterministic controls.

### Autonomous Stage D — Autonomous Risk Engine

Connect every AI decision to deterministic position, exposure, loss, drawdown, order-rate, liquidity, freshness, and portfolio constraints. Risk rejection is final.

### Autonomous Stage E — Autonomous Execution Loop

Create the continuously running decision-to-order loop using the existing execution abstraction, idempotency, outbox, exchange events, reconciliation, and accounting safeguards.

### Autonomous Stage F — Position & Portfolio Agent

Enable autonomous position maintenance: exits, stops, take-profit handling, stale-order cleanup, exposure balancing, and portfolio-level decisions, all bounded by deterministic policy.

### Autonomous Stage G — Continuous Strategy Learning

Evaluate live performance and drift, compare against expected behavior, retire degraded strategies, and generate replacement candidates. Learning must not silently mutate an active strategy version.

### Autonomous Stage H — Autonomous Promotion

Replace manual promotion as the normal operating path with policy-based automated promotion between research, paper, testnet, canary, limited, and live stages. Capital and risk ceilings remain deterministic.

### Autonomous Stage I — Autonomous Reliability & Recovery

Add process supervision, reconnect/recovery workflows, exchange outage handling, reconciliation loops, state repair, stale decision expiry, and autonomous safe shutdown.

### Autonomous Stage J — Production Autonomous Mode

Enable autonomous live operation only when all autonomous-specific evidence, reliability, risk, security, and recovery gates pass.

## Non-negotiable boundaries

- AI never receives raw Binance API secrets.
- AI never directly calls Binance.
- AI cannot override risk decisions.
- AI cannot disable the kill switch or circuit breaker.
- AI cannot increase capital limits on its own.
- AI cannot mutate an active immutable strategy version.
- Every autonomous decision is persisted with a deterministic decision ID and policy snapshot.
- Every order remains subject to deterministic preflight and execution authorization.
- Unknown exchange state is reconciled before further dependent actions.
- Stale market data or stale AI decisions fail closed.
- Autonomous mode must have a hard global disable control.
- The system must be able to safely stop opening new positions while continuing reconciliation and exit management where policy permits.

## First implementation target

The first implementation on this branch is **Autonomous Stage A — Autonomous Trading Control Plane**. It establishes the state machine and policy boundary before any autonomous order generation is enabled.
