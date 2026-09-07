# AI Trading Platform — Application User Guide

## 1. What this application is

The AI Trading Platform is a research-first quantitative trading application. It helps an operator move from a trading research idea to a validated strategy and, when all safety and authorization requirements are satisfied, through controlled trading environments.

The key design principle is:

> **AI proposes; deterministic software evaluates and controls; humans authorize live capital.**

The application is not an autonomous AI money manager. A good AI explanation or profitable backtest is never sufficient to authorize live trading.

## 2. Who should use it

### Researcher

Uses the platform to define research objectives, generate strategy candidates, run experiments and evaluate results.

### Quant / Strategy Engineer

Reviews strategy definitions, indicators, entry/exit logic, risk parameters, backtests and validation results.

### Risk Manager

Reviews risk limits, promotion evidence and live authorization requests. A Risk Manager is one of the required independent roles for live authorization.

### Administrator

Provides the second required independent approval for live authorization and oversees operational controls.

### Operator

Monitors health, queues, reconciliation, trading controls, alerts and promotion state. Operators should stop activity when the system enters an unsafe or unknown state.

## 3. Application components

The platform has two user-facing/control surfaces:

```text
Laravel Control Dashboard
        |
        v
FastAPI Control API
        |
        +--> Research
        +--> Backtesting / Validation
        +--> Risk / Controls
        +--> Promotion
        +--> Trading / Execution services
```

Supporting infrastructure includes PostgreSQL, Redis and RabbitMQ. Monitoring is provided through the observability stack.

The Laravel dashboard is intentionally lightweight. Its purpose is operational visibility and control-plane status, not unrestricted exchange trading.

## 4. First-time setup

### Step 1 — Start the platform

For the development environment, copy the environment template and start the infrastructure:

```bash
cp .env.example .env

docker compose up -d
```

The repository's Docker Compose setup provides PostgreSQL, RabbitMQ, Redis, migrations and the FastAPI API service.

### Step 2 — Check service health

Open:

```text
http://localhost:8000/health
```

A healthy response confirms that the control API is reachable.

### Step 3 — Open the Laravel dashboard

Start the dashboard according to the Laravel deployment instructions and open the configured dashboard URL.

The dashboard overview shows:

- current trading environment;
- whether trading is enabled;
- Control API health;
- live fail-closed posture;
- promotion gate status;
- safety boundary status.

## 5. Default safety posture

A fresh installation is intended to start safely:

```text
Environment: PAPER
Trading enabled: FALSE
Kill switch: TRUE
Live credentials: NOT exposed to the dashboard
Live order submission: NOT available from the dashboard
```

The repository environment template explicitly uses paper mode and disabled trading by default. Never change these settings merely to make the UI show a different status; follow the promotion and authorization process.

## 6. Understanding the dashboard

### Overview

The Overview page is the main operational landing page.

#### Environment

Shows the configured trading environment, such as `PAPER`, `TESTNET` or `LIVE`.

#### Trading enabled

Shows whether the trading subsystem is enabled by configuration. `DISABLED` is the expected initial state.

#### Control API

Shows whether the Laravel dashboard can reach the FastAPI `/health` endpoint.

Possible states include:

- **HEALTHY** — API responded successfully.
- **DEGRADED** — API responded with an unsuccessful HTTP status.
- **UNREACHABLE** — API could not be reached.

#### Live posture

The dashboard presents the system as fail-closed. This means a missing, invalid or stale safety condition should prevent live progression rather than silently allowing it.

### Promotion gates

The dashboard exposes the conceptual state of:

- Production readiness
- Two-person authorization
- Live canary
- Limited live
- Full live

These are gates, not buttons for bypassing the promotion process.

### Risk & Safety

The dashboard exposes the safety boundary around:

- kill switch;
- circuit breaker;
- exchange credentials;
- exchange order submission.

Credentials are deliberately not displayed in the dashboard.

## 7. Research workflow

The normal research workflow is:

```text
Research objective
      ↓
AI-generated hypotheses
      ↓
Structured strategy candidates
      ↓
Deterministic backtest
      ↓
Validation
      ↓
Walk-forward analysis
      ↓
Parameter sensitivity
      ↓
Monte Carlo analysis
      ↓
AI critic review
      ↓
Research gate
      ↓
Immutable strategy version
```

### Create a research session

Use the Control API:

```http
POST /api/v1/research-sessions
```

The request should describe the research objective and relevant constraints.

### Start the session

```http
POST /api/v1/research-sessions/{id}/start
```

### Monitor progress

```http
GET /api/v1/research-sessions/{id}
GET /api/v1/research-sessions/{id}/experiments
GET /api/v1/experiments/{id}
```

Long-running work is queued instead of being performed synchronously inside the HTTP request.

## 8. How to evaluate a strategy

When reviewing a strategy candidate, check:

1. **Hypothesis** — Can you explain why the strategy should work?
2. **Market** — Is the symbol and market appropriate for the experiment?
3. **Timeframe** — Is the timeframe intentional?
4. **Entry rules** — Are they deterministic and reproducible?
5. **Exit rules** — Are stop, target and other exits explicit?
6. **Sizing** — Is position sizing defined independently of AI output?
7. **Costs** — Are fees and slippage represented?
8. **Trade count** — Is there enough data to make the result meaningful?
9. **Drawdown** — Is the downside acceptable under the configured policy?
10. **Robustness** — Does performance survive walk-forward, sensitivity and Monte Carlo checks?
11. **Lineage** — Can the exact strategy version and fingerprint be reproduced?

Never optimize repeatedly against the final test set.

## 9. Backtesting

Backtesting is deterministic. It evaluates a structured strategy against historical market data and calculates metrics such as:

- entries and exits;
- fees;
- slippage;
- position sizing;
- realized P&L;
- equity curve;
- drawdown;
- returns;
- trade count;
- risk-adjusted performance measures.

Backtest numbers are evidence for research, not a promise of future performance.

## 10. Paper trading

Paper trading is the safest way to observe how a strategy behaves continuously.

Paper mode:

- consumes market data;
- generates signals;
- applies the risk gateway;
- creates simulated order activity;
- tracks positions and portfolio equity;
- performs accounting and reconciliation;
- never submits an exchange order.

Use paper trading to identify problems before Testnet.

## 11. Binance Spot Testnet

Testnet validates exchange integration without using production capital.

The expected workflow is:

```text
Market data
  → Signal
  → Risk check
  → Preflight
  → Order intent
  → Execution worker
  → Binance Spot Testnet
  → Exchange events / REST recovery
  → Reconciliation
  → Accounting
```

Verify account access and exchange filters before testing orders. Test partial fills, cancellations, rejected orders, timeouts, duplicate messages and recovery scenarios.

An `UNKNOWN` order must be reconciled before another submission is attempted.

## 12. Risk controls

Risk decisions sit between strategy signals and execution.

The platform is designed around a hierarchy similar to:

```text
Global risk
   ↓
Environment risk
   ↓
Strategy risk
   ↓
Symbol risk
   ↓
Order risk
```

Typical controls include position limits, total exposure, daily loss, drawdown, open-position limits, order-rate limits, kill switches and circuit breakers.

The exact configured values must be treated as policy. Prototype values in source code are not recommendations for live capital.

## 13. Promotion to live

A user should not jump directly from research to live trading.

The application uses:

```text
RESEARCH
   ↓
PAPER
   ↓
TESTNET
   ↓
LIVE CANARY
   ↓
LIVE LIMITED
   ↓
LIVE
```

Every live step is bound to the exact strategy version and relevant risk configuration.

### Production readiness

A strategy may become eligible only after the required evidence has passed. Eligibility does not itself authorize live capital.

### Two-person authorization

Live authorization requires independent approval. The requester cannot approve their own request. Required roles include Risk Manager and Administrator.

### Canary

Canary uses a deliberately small approved allocation and strict limits. If reconciliation, risk or execution health becomes unsafe, stop and halt the promotion.

### Limited live

Scaling is explicit and bounded. A material change requires fresh authorization.

### Full live

Full live requires all required evidence and controls to be healthy, including successful prior live stages, reconciliation health, circuit-breaker state, deliberate live arming and correct production configuration.

## 14. Kill switch and emergency response

If you suspect an unsafe condition:

1. Enable the kill switch.
2. Halt the relevant promotion/controller.
3. Stop scaling.
4. Reconcile exchange orders and balances.
5. Resolve any UNKNOWN order before retrying.
6. Preserve logs and audit information.
7. Determine the cause.
8. Obtain fresh authorization if a material configuration changed.

Do not bypass safety gates during an incident.

## 15. Common operator scenarios

### API says UNREACHABLE

Check:

- API container/process is running;
- port `8000` is available;
- PostgreSQL, Redis and RabbitMQ dependencies are healthy;
- network/DNS configuration is correct;
- API logs for startup or dependency failures.

### Trading is unexpectedly disabled

This is not automatically an error. Confirm the environment and intended operating mode first. The default posture is disabled paper trading.

### Testnet order appears stuck

Do not immediately resubmit it. Query the exchange and reconciliation state. Treat the order as potentially accepted until evidence proves otherwise.

### Risk gate rejects an order

Review the persisted risk decision and the relevant limit. Do not remove the risk control just to allow the order.

### Strategy fingerprint changed

Treat this as a new strategy version for promotion purposes. Do not reuse an authorization created for the previous fingerprint.

### Dashboard is healthy but live trading is unavailable

This is expected when one of the deeper promotion, authorization, risk, reconciliation or execution gates has not passed. Dashboard health is not equivalent to live eligibility.

## 16. What the application does not do

The application does not:

- guarantee profitable trading;
- allow AI to directly submit arbitrary exchange orders;
- expose Binance secrets to the research model;
- treat a backtest as live authorization;
- allow a dashboard health check to override a promotion gate;
- silently retry an UNKNOWN order;
- allow a changed strategy to reuse stale live authorization.

## 17. Recommended daily workflow

### Before research

- Confirm API health.
- Confirm data availability.
- Confirm the intended environment.
- Confirm trading remains disabled unless a controlled environment is deliberately being tested.

### Before Testnet

- Confirm Testnet credentials are correctly scoped.
- Confirm exchange filters.
- Confirm risk policies.
- Confirm kill switch and circuit breaker behavior.
- Confirm reconciliation is healthy.

### Before live

- Confirm production-readiness evidence.
- Confirm exact strategy version and fingerprint.
- Confirm risk-policy fingerprint.
- Confirm approved capital.
- Confirm two-person authorization.
- Confirm canary/limited-live evidence.
- Confirm account and reconciliation health.
- Confirm live endpoint and environment isolation.

### After live activity

- Review orders and fills.
- Review reconciliation.
- Review exposure and P&L.
- Review risk rejections and alerts.
- Review UNKNOWN states.
- Review operator/audit events.

## 18. Quick reference

| Task | Where |
|---|---|
| Check API | `GET /health` |
| Create research session | `POST /api/v1/research-sessions` |
| Start research | `POST /api/v1/research-sessions/{id}/start` |
| View session | `GET /api/v1/research-sessions/{id}` |
| View experiments | `GET /api/v1/research-sessions/{id}/experiments` |
| View experiment | `GET /api/v1/experiments/{id}` |
| View operational status | Laravel dashboard `/` |
| Configure environment | `.env` / deployment configuration |
| Configure production secrets | Secret manager / Kubernetes Secret |
| Emergency stop | Kill switch / promotion halt |

## 19. Important distinction

There are three different concepts that operators must not confuse:

**Application health** — the services are running.

**Promotion eligibility** — the strategy and evidence have satisfied the required gates.

**Live authorization** — authorized humans have approved the exact strategy, risk policy and capital allocation for live execution.

A system can be healthy without being eligible, and eligible without having live authorization.
