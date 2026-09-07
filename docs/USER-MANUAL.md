# AI Trading Platform — User Manual

## 1. Purpose

This platform is a research-first, AI-assisted quantitative trading system. AI proposes hypotheses and structured strategy candidates; deterministic software performs backtesting, validation, risk checks, execution controls, accounting and reconciliation. Humans authorize live capital.

**Default posture:** paper trading, trading disabled, kill switch enabled.

Never interpret a strategy suggestion, backtest result, or AI review as a guarantee of profit.

## 2. Operating Modes

| Mode | Purpose | Exchange orders |
|---|---|---|
| Research | Generate and evaluate ideas | No |
| Paper | Simulate trading against market data | No |
| Testnet | Validate exchange integration | Testnet only |
| Live Canary | First controlled production allocation | Only after all gates |
| Live Limited | Controlled scaling | Only after re-authorization |
| Live | Full approved allocation | Only after full-live gate |

## 3. Normal User Journey

1. Start infrastructure.
2. Confirm `/health` is healthy.
3. Create a research session.
4. Define the research objective.
5. Let the AI researcher propose structured candidates.
6. Run deterministic backtests.
7. Run validation, walk-forward, sensitivity and Monte Carlo checks.
8. Review the AI critic output.
9. Pass the research gate.
10. Freeze an immutable strategy version.
11. Run paper trading and the paper gate.
12. Run Binance Spot Testnet E2E and failure/soak validation.
13. Run production-readiness evidence collection.
14. Obtain independent two-person authorization if live promotion is justified.
15. Run canary, then limited live, then full live only when each gate passes.

## 4. Research Workflow

### Create a research session

Use the control API endpoint:

```http
POST /api/v1/research-sessions
```

The request should identify the objective and constraints. Long-running work is queued rather than executed synchronously.

### Start a session

```http
POST /api/v1/research-sessions/{id}/start
```

Monitor the session and its experiments:

```http
GET /api/v1/research-sessions/{id}
GET /api/v1/research-sessions/{id}/experiments
GET /api/v1/experiments/{id}
```

### Review a strategy

Confirm:

- strategy family and hypothesis are understandable;
- symbol and timeframe are intentional;
- entry and exit conditions are deterministic;
- risk parameters are explicit;
- the fingerprint is recorded;
- the candidate is not an accidental duplicate;
- train/validation/final-test separation is maintained.

## 5. Backtesting and Validation

Backtests model fees, slippage, position sizing, stop loss, take profit, P&L, equity and drawdown. Prototype values in the repository are test defaults and are **not trading recommendations**.

Do not promote a strategy because of one attractive backtest. Review trade count, drawdown, walk-forward behavior, parameter stability and Monte Carlo results.

The final test set must remain sealed from iterative tuning.

## 6. Paper Trading

Paper trading uses market data and the same signal/risk concepts as later environments but does not submit exchange orders.

Before trusting paper results, confirm:

- completed-candle processing is used;
- indicator warm-up is sufficient;
- risk decisions are persisted;
- orders and fills are internally consistent;
- equity and P&L reconcile;
- kill switch behavior works.

## 7. Testnet Operation

Testnet is for integration validation, not proof of profitability.

A testnet smoke test should verify account access and symbol filters before attempting any test order. Validate order acknowledgement, fills, cancellations, WebSocket events, REST recovery and reconciliation.

Unknown orders must be reconciled before any retry.

## 8. Promotion Workflow

Promotion is strictly sequential:

```text
RESEARCH → PAPER → TESTNET → LIVE_CANARY → LIVE_LIMITED → LIVE
```

A live promotion must bind the exact strategy version, strategy fingerprint, risk-policy fingerprint, approved capital and evidence snapshot.

### Two-person authorization

The requester cannot approve their own promotion. Live authorization requires independent approvals including the required Risk Manager and Admin roles. Material changes invalidate the authorization.

### Canary

Canary starts disarmed. Arm only after authorization and gate checks pass. If reconciliation, risk or execution health becomes unsafe, halt immediately.

### Limited live

Scaling is explicit and bounded by the original approved allocation. A new authorization is required for material changes.

### Full live

Full live requires successful canary and limited-live evidence, healthy account/reconciliation state, closed circuit breaker, disabled kill switch, explicit live arm, correct production endpoint and valid production configuration.

## 9. Laravel Dashboard

The dashboard is an observability/control surface. It is intentionally not a secret store and does not provide an unrestricted Binance trading console.

Use it to review:

- service health;
- current environment;
- trading-enabled state;
- kill-switch state;
- promotion state;
- safety boundaries;
- operational readiness.

A dashboard showing LIVE eligibility does not itself authorize capital.

## 10. Emergency Controls

When anything is uncertain:

1. Enable the kill switch.
2. Halt the relevant promotion/controller.
3. Stop scaling.
4. Reconcile orders and balances using REST recovery.
5. Identify UNKNOWN orders before retrying.
6. Preserve logs and audit events.
7. Investigate the root cause.
8. Require fresh approval if a material configuration changed.

Fail closed. Do not bypass a gate manually just to resume trading.

## 11. Daily Operator Checklist

- [ ] API health is green.
- [ ] Database is healthy and backed up.
- [ ] RabbitMQ queues are healthy; no critical dead letters.
- [ ] Redis is healthy.
- [ ] Reconciliation has no unresolved discrepancies.
- [ ] No UNKNOWN orders remain.
- [ ] Circuit breaker is in the expected state.
- [ ] Kill switch state is intentional.
- [ ] Current strategy version/fingerprint is known.
- [ ] Risk policy fingerprint is known.
- [ ] Capital allocation matches authorization.
- [ ] Monitoring and alerts are functioning.
- [ ] Recent operator actions are reviewed.

## 12. What Users Must Never Do

- Put API secrets into AI prompts.
- Commit real credentials to Git.
- Enable live trading by changing only an environment variable.
- Reuse an authorization after changing strategy/risk/capital.
- Blindly retry an UNKNOWN exchange order.
- Disable reconciliation to make a deployment look healthy.
- Treat backtest performance as a guarantee.
- Give research workloads access to live credentials.
