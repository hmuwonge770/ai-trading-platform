# AI Trading Platform

**Research-first, AI-assisted quantitative trading platform.**

> **AI is the research scientist, not the trader.** AI generates hypotheses and structured strategy candidates. Deterministic software owns backtesting, validation, risk, execution, accounting, reconciliation and promotion. Humans authorize live capital.

## End-to-end lifecycle

```text
Market Data
  -> AI Research
  -> Strategy Specification
  -> Backtesting
  -> Validation
  -> Robustness / Anti-Overfitting
  -> AI Critic
  -> Research Gate
  -> Immutable Strategy Version
  -> Paper Trading
  -> Paper Gate
  -> Binance Spot Testnet
  -> E2E / Failure Testing / Soak
  -> Production Readiness Gate
  -> Two-Person Approval
  -> LIVE_CANARY
  -> LIVE_LIMITED
  -> LIVE
```

Live trading is fail-closed by default.

---

# Stages 1–34

## Stage 1 — Architecture

Separate the AI research plane from deterministic trading/execution:

```text
Laravel/Inertia Control UI -> FastAPI Control API
                              |
                 +------------+-------------+
                 |            |              |
              Research    Backtest        Control
                 |            |              |
                AI       Validation       Risk
                 |            |              |
                 +------------+-------------+
                              |
                         Paper Trading
                              |
                           Testnet
                              |
                       Live Authorization
                              |
                          Execution
                              |
                           Binance
```

Stack: Python, FastAPI, Laravel/Inertia, PostgreSQL, Redis, RabbitMQ, Docker, Kubernetes, Prometheus/Grafana, Binance Spot API/WebSockets.

## Stage 2 — Research-only V1

Bootstrap PostgreSQL, RabbitMQ and Redis. No order submission. Initial local configuration:

```env
DATABASE_URL=postgresql+psycopg://trading:trading_dev_password@localhost:5433/trading_research
REDIS_URL=redis://localhost:6379/0
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
BINANCE_BASE_URL=https://api.binance.com
OPENAI_API_KEY=
```

## Stage 3 — Market Data

Download and persist historical candles: symbol, timeframe, timestamps, OHLCV, quote volume and trade count. Research operates on reproducible stored datasets.

## Stage 4 — Strategy Engine

Strategies are structured configurations, not arbitrary executable AI code:

```text
Strategy -> family, hypothesis, symbol, timeframe,
            indicators, entry_conditions, exit_conditions, risk
```

Initial indicator/condition examples include EMA and RSI. Strategy configurations receive deterministic fingerprints.

## Stage 5 — Backtesting

Deterministic backtester models entries, exits, sizing, fees, slippage, stop loss, take profit, P&L, equity, drawdown, returns, Sharpe-style metrics and trade count. Prototype values included 2% position size, 2% stop, 4% target, 0.1% fee and 0.05% slippage; these are test values, not recommendations.

## Stage 6 — Experiment Management

Persist `ResearchSession`, `Strategy`, `StrategyVersion`, `Experiment`, `BacktestResult`, `AIReview` and `ResearchHypothesis`. Record lineage and prevent duplicate strategy fingerprints.

## Stage 7 — AI Researcher

AI reads the objective and experiment history, proposes hypotheses and structured strategy candidates, explains expected effects and avoids previously tested configurations. It never receives exchange secrets or direct order permissions.

## Stage 8 — AI Experiment Orchestrator

```text
Objective -> History -> AI -> Strategy -> Backtest -> Validation
          -> Critic -> Research Gate -> History -> Next Experiment
```

Governance includes experiment limits, per-strategy limits, minimum trade counts, fingerprints and lineage.

## Stage 9 — RabbitMQ

Durable asynchronous queues:

```text
research.generate[.retry|.dead]
experiment.backtest[.retry|.dead]
validation.run[.retry|.dead]
critic.review[.retry|.dead]
execution.submit[.retry|.dead]
execution.reconcile[.retry|.dead]
```

Jobs carry IDs, type, session/experiment IDs, payload, attempts, errors and timestamps. Workers are idempotent; critical execution/reconciliation dead letters require operator attention.

## Stage 10 — Research API

Core endpoints:

```http
POST /api/v1/research-sessions
GET  /api/v1/research-sessions/{id}
POST /api/v1/research-sessions/{id}/start
GET  /api/v1/research-sessions/{id}/experiments
GET  /api/v1/experiments/{id}
GET  /health
```

HTTP requests enqueue long-running work rather than performing it synchronously.

## Stage 11 — Lineage & Anti-Overfitting

Use train/validation/final-test separation, walk-forward testing, parameter sensitivity and Monte Carlo trade-P&L shuffling. Keep the final test sealed from iterative research. Illustrative gates:

```text
test_return > 0
walk_forward_sharpe >= 0.8
positive_window_ratio >= 0.60
parameter_stability >= 0.70
monte_carlo_worst_drawdown <= 0.40
```

These are policy examples, not profitability guarantees. Deterministic gates decide; AI commentary cannot override them.

## Stage 12 — Paper Trading

Live market data feeds strategy signals, risk and a simulated executor. Paper mode never submits exchange orders. Strategies act on completed candles and warm up from historical data.

`TradingSignal` contains signal ID, strategy/version, symbol, side, reference price, timestamps and reason. `OrderIntent` contains intent ID, strategy/version, symbol, side, type, quantity, reference price, client ID and reason.

## Stage 13 — Portfolio & Money

Use `Decimal` and PostgreSQL `NUMERIC`. `PaperPortfolio`, `PaperPosition` and `EquitySnapshot` track cash, initial/current equity, realized/unrealized P&L, peak equity, drawdown, average entry and exposure.

## Stage 14 — Risk Gateway

Risk hierarchy:

```text
Global -> Environment -> Strategy -> Symbol -> Order
```

Initial policy examples include max position 2%, total exposure 20%, daily loss 3%, drawdown 15%, five open positions and ten orders/minute. Every risk decision is persisted. Kill switches and circuit breakers fail closed.

## Stage 15 — Execution Simulator

Test the state machine before exchange execution:

```text
CREATED -> RISK_CHECK -> APPROVED -> SUBMITTED -> ACKNOWLEDGED
         -> PARTIALLY_FILLED -> FILLED
```

Failure cases include normal/partial fills, rejection, timeout, timeout-after-accept, duplicate message, worker/database/RabbitMQ failure, stale price, insufficient balance, kill switch, balance/position mismatch and exchange outage. `UNKNOWN` orders are reconciled, never blindly retried.

## Stage 16 — Execution Service

Exchange abstraction:

```text
get_account
get_symbol_info
create_order
get_order
get_open_orders
get_trades
cancel_order
```

Validate Binance filters: minimum/maximum quantity, step size, minimum notional and tick size. Persist client IDs before submission. Use database row locks around portfolio/order accounting.

## Stage 17 — Binance Spot Testnet

Implement REST signing, exchange information, account state, orders, fills, cancellation, WebSocket market data and authenticated user-data events. REST is used for recovery/reconciliation; event processing is idempotent.

Testnet flow:

```text
Signal -> Risk -> Preflight -> Local Order -> Outbox -> RabbitMQ
       -> Execution Worker -> Binance Testnet -> User Data/REST
       -> Reconciliation -> Fills -> Accounting -> Portfolio/Metrics
```

Smoke tests verify credentials/account/exchange filters before any order.

## Stage 18 — Accounting & Transactions

Critical transaction:

```text
BEGIN -> lock portfolio/position -> validate risk/version
-> update order -> apply fills -> cash -> position -> P&L
-> equity snapshot -> audit event -> COMMIT
```

Rollback on failure. Prevent concurrent workers from corrupting balances or positions.

## Stage 19 — Observability

Prometheus/Grafana metrics include orders, latency, active positions, equity, risk rejections, unknown orders, drawdown, exposure and daily P&L. Structured JSON logs and correlation IDs connect signal -> risk -> order -> exchange -> fill -> accounting.

## Stage 20 — Outbox & Reliability

Persist business state and an outbox event in one database transaction; an outbox worker publishes to RabbitMQ. Retry with controlled backoff and dead-letter permanently failing jobs. Reconciliation/execution failures are critical alerts.

## Stage 21 — Security, Failure & Soak

Kubernetes isolation:

```text
trading-research
trading-paper
trading-testnet
trading-live
monitoring
```

Research has no exchange credentials. Testnet gets Testnet credentials only. Live gets Live credentials only. Use RBAC, NetworkPolicies, secret management, minimum Binance permissions, withdrawals disabled and IP restrictions where available. Keep API secrets out of AI prompts/logs.

Run deterministic failure scenarios and a 72-hour soak with controlled restarts of workers, API, RabbitMQ, Redis, WebSockets and database connections. Verify no duplicate orders, lost fills, negative balances, corrupted positions or unresolved unknown orders.

## Stage 22 — Promotion & Live Authorization

Promotion stages:

```text
RESEARCH -> PAPER -> TESTNET -> LIVE_CANARY -> LIVE_LIMITED -> LIVE
```

The foundation provides immutable strategy-version fingerprint binding, promotion state, two-person approval, Risk Manager + Admin roles, requester self-approval protection, duplicate-approver protection, capital limits, evidence hashes, authorization snapshots, SHA-256 authorization hashes, expiration, risk-policy fingerprint binding, fail-closed preflight, endpoint isolation and a bounded canary controller.

## Stage 23 — PostgreSQL Promotion Repository

Replace temporary process-local promotion state with PostgreSQL repositories and transactional row locking. Persist promotions, approvals, allocations and authorization snapshots. Approval/activation must be atomic and race-safe.

## Stage 24 — Promotion Control API

Expose authenticated request, approve, reject, activate, halt and scale operations. Audit every operator action. Generate authorization only from persisted state.

## Stage 25 — Full Execution Integration

Connect promotion authorization to the execution worker. Immediately before exchange submission verify strategy version, fingerprint, authorization, allocation, risk policy, kill switch, circuit breaker, account, reconciliation and market freshness.

## Stage 26 — Testnet E2E

Run the complete controlled Testnet session from market data through fills, accounting, reconciliation and metrics. Compare backtest, paper and Testnet behavior and investigate divergence.

## Stage 27 — Failure & Property Testing

Use Hypothesis/property testing and deterministic seeds to execute thousands of scenarios. Assert no duplicate orders, no negative balances/positions, fills <= requested quantity, equity/P&L consistency, risk limits respected and UNKNOWN states reconciled.

## Stage 28 — 72-hour Soak

Run the complete platform continuously while deliberately restarting components and injecting network/exchange failures. Track memory, queue depth, reconnects, dead letters, reconciliation and recovery.

## Stage 29 — Kubernetes Isolation

Deploy separate namespaces, service accounts, NetworkPolicies and secrets. Research cannot access live credentials. Testnet cannot reach the production endpoint. Live cannot use Testnet credentials. Invalid configuration fails closed.

## Stage 30 — Production Readiness

A strategy becomes `LIVE_ELIGIBLE`, not automatically live, only after research, paper, Testnet, security, failure, reconciliation, backup/restore, observability and soak gates pass.

## Stage 31 — Two-Person Live Authorization

The exact frozen strategy version, fingerprint, risk-policy fingerprint, capital allocation and evidence are approved by independent authorized humans. Changing any material value invalidates the authorization.

## Stage 32 — Live Canary

Start with deliberately small capital and strict position/loss/order limits. Canary states are `DISARMED`, `ARMED`, `ACTIVE`, `HALTED`. Scaling requires a passed canary gate: zero reconciliation errors, unresolved unknowns, balance/position mismatches, risk violations and critical execution errors.

## Stage 33 — Limited Live

Increase capital only through an explicit approved scaling workflow. Continue reconciliation, risk, circuit-breaker, performance and drift monitoring. Material strategy/configuration/risk-policy changes require a new version/authorization.

## Stage 34 — Full Live

Full live remains gated by immutable strategy version, matching fingerprints, approved capital, successful canary/limited stages, healthy account/reconciliation, closed circuit breaker, deliberately disabled kill switch, explicit live arm and correct production endpoint/credentials.

---

# Repository Structure

```text
ai-trading-platform/
├── apps/
│   ├── api/
│   │   ├── main.py
│   │   └── routes/
│   │       ├── health.py
│   │       ├── research.py
│   │       ├── experiments.py
│   │       ├── promotions.py
│   │       └── trading.py
│   └── workers/
│       ├── research_worker.py
│       ├── backtest_worker.py
│       ├── validation_worker.py
│       ├── critic_worker.py
│       ├── execution_worker.py
│       ├── reconciliation_worker.py
│       └── outbox_worker.py
├── packages/
│   ├── database/
│   │   ├── base.py
│   │   ├── session.py
│   │   └── models/
│   │       ├── research.py
│   │       ├── trading.py
│   │       ├── risk.py
│   │       ├── execution.py
│   │       ├── promotion.py
│   │       └── operations.py
│   ├── trading/
│   │   ├── config.py
│   │   ├── money.py
│   │   ├── signals.py
│   │   ├── orders.py
│   │   ├── accounting.py
│   │   ├── portfolio.py
│   │   ├── environment.py
│   │   └── paper.py
│   ├── strategies/
│   │   ├── schema.py
│   │   ├── engine.py
│   │   ├── indicators.py
│   │   └── fingerprint.py
│   ├── research/
│   │   ├── orchestrator.py
│   │   ├── researcher.py
│   │   ├── critic.py
│   │   ├── history.py
│   │   ├── experiments.py
│   │   ├── lineage.py
│   │   ├── gates.py
│   │   ├── walk_forward.py
│   │   ├── sensitivity.py
│   │   └── monte_carlo.py
│   ├── risk/
│   │   ├── gateway.py
│   │   ├── limits.py
│   │   ├── decisions.py
│   │   ├── controls.py
│   │   └── circuit_breaker.py
│   ├── exchange/
│   │   ├── interface.py
│   │   ├── models.py
│   │   ├── filters.py
│   │   ├── paper.py
│   │   └── binance/
│   │       ├── __init__.py
│   │       ├── client.py
│   │       ├── signer.py
│   │       ├── websocket.py
│   │       └── mapper.py
│   ├── messaging/
│   │   ├── publisher.py
│   │   ├── consumer.py
│   │   ├── jobs.py
│   │   ├── queues.py
│   │   └── retry.py
│   ├── observability/
│   │   ├── metrics.py
│   │   ├── logging.py
│   │   ├── events.py
│   │   └── correlation.py
│   └── promotion/
│       ├── __init__.py
│       ├── domain.py
│       ├── service.py
│       ├── preflight.py
│       └── canary.py
├── migrations/
│   └── versions/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── failure/
│   └── property/
├── scripts/
│   ├── download_market_data.py
│   ├── run_research.py
│   ├── run_backtest.py
│   ├── run_validation.py
│   ├── run_testnet_smoke.py
│   ├── run_failure_suite.py
│   ├── run_soak_test.py
│   └── verify_production_readiness.py
├── docker/
├── k8s/
│   ├── namespaces/
│   ├── research/
│   ├── paper/
│   ├── testnet/
│   ├── live/
│   ├── monitoring/
│   ├── network-policies/
│   └── service-accounts/
├── monitoring/
│   ├── prometheus/
│   └── grafana/dashboards/
├── docker-compose.yml
├── pyproject.toml
├── alembic.ini
├── .env.example
└── README.md
```

# Database Model

```text
Research:
  research_sessions, strategies, strategy_versions,
  research_hypotheses, experiments, backtest_results, ai_reviews

Trading:
  trading_signals, trading_orders, order_fills,
  paper_portfolios, paper_positions, equity_snapshots

Risk:
  risk_limits, risk_decisions, risk_decision_logs, trading_controls

Execution:
  execution_attempts, execution_events, outbox_events,
  reconciliation_results

Promotion:
  strategy_promotions, promotion_approvals,
  capital_allocations, authorization_snapshots

Operations:
  operator_actions, trading_alerts
```

# Core Execution Pipeline

```text
Market Data
 -> Strategy Version
 -> Trading Signal
 -> Risk Gateway
 -> Order Intent
 -> Order Manager
 -> PostgreSQL + Outbox
 -> RabbitMQ
 -> Execution Worker
 -> Live Preflight
 -> Binance Adapter
 -> Exchange
 -> User Data / REST
 -> Reconciliation
 -> Order Fill
 -> Accounting
 -> Portfolio
 -> Metrics / Audit
```

# Production Safety Invariants

1. AI never directly submits orders.
2. AI cannot bypass risk.
3. AI cannot approve itself.
4. Configuration changes create new strategy versions.
5. Fingerprint mismatch blocks execution.
6. Risk-policy mismatch blocks execution.
7. Expired authorization blocks execution.
8. Kill switch blocks new orders.
9. Open circuit breaker blocks new orders.
10. Reconciliation mismatch blocks new orders.
11. UNKNOWN exchange states require reconciliation.
12. Testnet and production credentials are isolated.
13. Research workers have no exchange secrets.
14. Capital increases require controlled authorization.
15. Live trading is disabled by default.

# Production Readiness Checklist

### Research
- [ ] historical data sufficient
- [ ] trade count sufficient
- [ ] out-of-sample passed
- [ ] walk-forward passed
- [ ] sensitivity passed
- [ ] Monte Carlo robustness passed
- [ ] AI critic reviewed

### Paper
- [ ] minimum paper activity
- [ ] backtest/paper divergence understood
- [ ] accounting consistent
- [ ] no unexplained risk violations

### Testnet
- [ ] credentials/account verified
- [ ] exchange filters verified
- [ ] normal and partial fills verified
- [ ] rejection verified
- [ ] timeout/UNKNOWN recovery verified
- [ ] reconciliation verified
- [ ] accounting verified

### Security/Operations
- [ ] secret isolation
- [ ] RBAC and NetworkPolicies
- [ ] minimum API permissions
- [ ] withdrawals disabled
- [ ] structured audit logs
- [ ] backup and restore drill
- [ ] 72-hour soak passed

### Live
- [ ] immutable version
- [ ] matching fingerprint
- [ ] matching risk-policy fingerprint
- [ ] approved capital
- [ ] Risk Manager approval
- [ ] Admin approval
- [ ] canary passed
- [ ] limited-live passed
- [ ] reconciliation healthy
- [ ] circuit breaker closed
- [ ] live explicitly armed

# Guiding Principle

The objective is not to make the AI trade as much as possible. The objective is to produce an auditable chain of evidence:

```text
Why was the strategy created?
What hypothesis did it test?
What data was used?
Did it survive out-of-sample testing?
Did it survive robustness tests?
Did it work in paper trading?
Did Testnet execution behave correctly?
Did reconciliation remain correct?
Who approved it?
Which exact strategy version was approved?
How much capital was approved?
Which risk policy was approved?
Why was each order allowed?
What happened after the order?
```

**AI discovers. Deterministic systems verify. Humans authorize. Risk controls enforce. The exchange executes. Reconciliation proves what happened.**
