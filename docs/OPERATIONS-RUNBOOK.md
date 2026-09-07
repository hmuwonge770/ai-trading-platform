# AI Trading Platform — Operations Runbook

## 1. Golden Rules

1. Fail closed.
2. Never bypass a safety gate.
3. Never treat AI output as execution authority.
4. Never retry an UNKNOWN exchange order blindly.
5. Reconcile before resuming after an execution incident.
6. Material strategy, risk or capital changes require a new immutable version/authorization.
7. Keep production credentials isolated from research and paper workloads.

## 2. Service Map

```text
Laravel Dashboard
        |
        v
FastAPI Control API
   |       |       |
Postgres Redis RabbitMQ
                 |
          +------+------+
          |             |
       Workers       Outbox
          |
     Exchange adapter
          |
   Binance Testnet/Live
          |
 Reconciliation
          |
 Accounting / Metrics
```

## 3. Startup Order

```text
PostgreSQL
RabbitMQ
Redis
migrations
API
workers
monitoring
Laravel dashboard
```

Verify each dependency before starting the next layer.

## 4. Health Checks

API:

```bash
curl http://localhost:8000/health
```

Docker:

```bash
docker compose ps
docker compose logs --tail=200 api
```

Kubernetes:

```bash
kubectl get pods -A
kubectl get events -A --sort-by=.lastTimestamp
```

RabbitMQ: check consumers, queue depth, retry queues and dead-letter queues.

PostgreSQL: check connections, locks, replication/backup state and migration version.

Redis: check availability, memory and persistence behavior.

## 5. Pre-Session Checklist

- [ ] Correct Git/image version deployed.
- [ ] CI passed for that commit.
- [ ] Configuration loaded from approved source.
- [ ] Environment and endpoint agree.
- [ ] Database migrations complete.
- [ ] Queue consumers healthy.
- [ ] No critical dead letters.
- [ ] Reconciliation healthy.
- [ ] No unresolved UNKNOWN orders.
- [ ] Kill switch state intentionally selected.
- [ ] Circuit breaker state understood.
- [ ] Current strategy version/fingerprint documented.
- [ ] Risk-policy fingerprint documented.
- [ ] Capital allocation matches approved authorization.

## 6. Research Incident

If research produces invalid or suspicious output:

1. Stop the research session.
2. Preserve experiment and AI review records.
3. Check strategy fingerprint/lineage.
4. Verify no execution permission exists.
5. Correct the research workflow.
6. Re-run deterministic validation.

Do not promote an unverified candidate because the AI explanation looks convincing.

## 7. Queue Incident

### Queue growing

Check:

```bash
# Docker
 docker compose logs rabbitmq
```

Then inspect worker health and dependency latency.

Do not increase retries indefinitely. Investigate the failing dependency.

### Dead letters

Critical execution/reconciliation dead letters require operator review. Identify the job, attempt count, error, correlation ID and related order/intent before retrying.

## 8. Execution Incident

Symptoms include:

- timeout;
- duplicate submission concern;
- exchange rejection;
- partial fill inconsistency;
- WebSocket disconnect;
- balance mismatch;
- position mismatch;
- UNKNOWN order.

Response:

1. Enable kill switch if live activity could continue unsafely.
2. Halt the relevant promotion/controller.
3. Stop new order submission.
4. Query exchange state with REST recovery.
5. Reconcile orders, fills, balances and positions.
6. Resolve UNKNOWN states deterministically.
7. Check idempotency/client IDs.
8. Check database/outbox/event ordering.
9. Record an operator incident.
10. Resume only after reconciliation and safety gates pass.

## 9. Database Failure

If PostgreSQL is unavailable:

- stop new execution;
- preserve exchange state;
- do not invent local balances;
- restore service;
- verify migrations;
- reconcile against exchange state;
- verify outbox and accounting consistency.

Never declare the system healthy solely because the database restarted.

## 10. RabbitMQ Failure

If the broker is unavailable:

- stop or fail closed on dependent asynchronous workflows;
- preserve transactional outbox records;
- restore broker connectivity;
- verify consumers and queues;
- replay only idempotent work;
- reconcile execution state before resuming.

## 11. Redis Failure

Treat Redis as unavailable until connectivity is verified. If any safety decision depends on cached/transient state, fail closed rather than assuming the cache is correct.

## 12. Binance Connectivity Failure

If Binance becomes unreachable:

1. Stop new live submissions.
2. Keep local state marked as potentially stale.
3. Reconnect market/user streams safely.
4. Use REST recovery for authoritative order state.
5. Reconcile before retrying.
6. Resume only when market/account freshness and safety gates pass.

## 13. UNKNOWN Order Procedure

An UNKNOWN order means local state cannot prove whether the exchange accepted the order.

Never create a second order merely because the first request timed out.

Use the original client order ID/order identifiers to query exchange state. Determine whether the order was rejected, accepted, partially filled, filled or cancelled. Then apply the authoritative result to accounting and close the UNKNOWN state.

## 14. Kill Switch

The kill switch is an emergency control, not a normal deployment mechanism.

When engaged:

- no new trading should be initiated;
- existing state must be reconciled;
- active promotion may need to be halted;
- investigation and evidence preservation take priority.

To clear it, verify the incident is resolved and perform the relevant gates again.

## 15. Circuit Breaker

A circuit breaker should remain closed before full-live activation. If it opens:

1. Stop new orders.
2. Inspect triggering metrics.
3. Reconcile exchange/local state.
4. Determine root cause.
5. Resolve the condition.
6. Require fresh evidence/authorization when a material condition changed.

## 16. Promotion Operations

### Request

Create a promotion for the exact immutable strategy version and intended stage.

### Approve

Required authorized roles approve the exact fingerprint and capital allocation.

### Activate

Activation requires the appropriate approval state and complete authorization.

### Halt

Halt immediately when safety conditions are breached.

### Scale

Scaling must stay within the originally approved allocation ceiling and requires a fresh clean gate/authorization as defined by the promotion controller.

## 17. Live Preflight

Before live activation verify all of the following:

```text
promotion approved/active
LIVE target
strategy frozen
exact strategy version
exact strategy fingerprint
exact authorization fingerprint
exact risk-policy fingerprint
approved capital matches authorization
canary passed
limited-live passed
account healthy
reconciliation healthy
circuit breaker closed
kill switch disabled
live explicitly armed
credentials configured
production endpoint exact
```

Any single failure blocks activation.

## 18. Monitoring

Track at minimum:

- API availability;
- worker health;
- queue depth;
- retry/dead-letter counts;
- order latency;
- rejected orders;
- UNKNOWN orders;
- reconciliation errors;
- account/position mismatches;
- exposure;
- drawdown;
- daily P&L;
- WebSocket reconnects;
- database health;
- Redis health;
- RabbitMQ health.

## 19. Incident Severity

### Critical

Uncontrolled live orders, unknown order state, balance/position mismatch, reconciliation failure, credential exposure or safety-control bypass.

**Action:** kill switch + halt + incident response.

### High

Repeated execution errors, broken monitoring, queue backlog affecting execution, circuit breaker activation.

**Action:** stop promotion/scaling and investigate immediately.

### Medium

Research failure, non-critical worker degradation, delayed analytics.

**Action:** repair before next promotion.

## 20. Post-Incident Review

Record:

```text
incident_id
start/end time
environment
Git SHA
strategy version
risk policy fingerprint
capital allocation
affected orders
exchange state
root cause
safety controls triggered
operator actions
reconciliation result
corrective actions
new tests added
```

## 21. Disaster Recovery

Recovery order:

```text
Infrastructure
→ PostgreSQL
→ RabbitMQ/Redis
→ API/workers
→ monitoring
→ reconciliation
→ dashboard
→ controlled resumption
```

Never resume live execution until exchange state and internal accounting are reconciled.
