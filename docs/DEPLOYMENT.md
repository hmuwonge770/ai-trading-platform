# AI Trading Platform — Deployment Guide

## 1. Deployment Principles

Deploy in this order:

```text
Infrastructure → Database migrations → API → Workers → Monitoring → Laravel dashboard → Validation → Promotion
```

Keep research, paper, testnet and live workloads isolated. Never promote directly from a developer workstation.

## 2. Requirements

Recommended production components:

- Linux host or Kubernetes cluster
- Python runtime matching `pyproject.toml`
- PHP runtime and Composer for `dashboard/`
- PostgreSQL
- Redis
- RabbitMQ
- Docker
- Kubernetes for isolated environments
- Prometheus/Grafana for monitoring
- Managed secret storage
- TLS termination and an authenticated operator network

## 3. Local Docker Deployment

The repository provides `docker-compose.yml` with PostgreSQL 17, RabbitMQ 4, Redis 8, a migration service and the FastAPI API.

```bash
cp .env.example .env

docker compose up -d postgres rabbitmq redis
docker compose run --rm migrate
docker compose up -d api
```

Verify:

```bash
curl http://localhost:8000/health
```

Expected result is a healthy API response. Check containers with:

```bash
docker compose ps
docker compose logs -f api
```

RabbitMQ management is exposed on port `15672` in the development compose file.

## 4. Local Laravel Dashboard

```bash
cd dashboard
composer install
cp .env.example .env
php artisan key:generate
php artisan serve
```

The dashboard is a control/observability surface. Keep its production deployment behind authentication, TLS and an operator-only network.

Configure the dashboard's FastAPI/control API URL using the application configuration provided in `dashboard/config/services.php` and the corresponding environment variable documented there.

## 5. Environment Configuration

The checked-in `.env.example` intentionally defaults to:

```env
APP_ENV=local
TRADING_ENVIRONMENT=paper
TRADING_ENABLED=false
TRADING_KILL_SWITCH=true
```

This is the correct initial posture.

Never copy development database passwords, RabbitMQ guest credentials, or example values into production.

## 6. Production Infrastructure

### PostgreSQL

Use managed PostgreSQL where possible. Requirements:

- encrypted connections;
- automated backups;
- point-in-time recovery where available;
- restricted network access;
- separate database/roles for environments;
- monitoring for connections, storage, locks and replication.

Before deployment:

```bash
alembic upgrade head
```

Run migrations once using a controlled migration job rather than concurrently from every API replica.

### Redis

Use Redis for transient state/queues/caching as implemented by the application. Enable authentication/TLS where supported by the deployment. Persist only data that the application's design explicitly requires.

### RabbitMQ

Use durable queues and persistent messages for critical workflows. Monitor queue depth, consumer health, retry queues and dead-letter queues. Restrict management UI access.

## 7. Docker API Deployment

Build the API image from `docker/api.Dockerfile`:

```bash
docker build -f docker/api.Dockerfile -t ai-trading-platform-api:<git-sha> .
```

Tag with an immutable Git SHA. Do not deploy mutable `latest` as the only production reference.

Run the migration image/job, then start API and workers. Pin image versions and record the deployed Git SHA.

## 8. Kubernetes Deployment

The repository's Kubernetes isolation model uses separate namespaces:

```text
trading-research
trading-paper
trading-testnet
trading-live
monitoring
```

Apply namespaces, service accounts, network policies and workloads in that order. Then configure environment-specific secrets.

Minimum isolation requirements:

- research has no exchange credentials;
- paper has no exchange order permission;
- testnet can reach only the Testnet endpoint;
- live can reach only the production Binance endpoint;
- service accounts use least privilege;
- NetworkPolicies deny unnecessary east-west traffic;
- secrets are supplied by a secret manager, not Git.

## 9. Kubernetes Secrets

Use the repository template only as a schema. It contains placeholders for:

```text
trading-testnet/testnet-binance
  BINANCE_API_KEY
  BINANCE_API_SECRET

trading-live/live-binance
  BINANCE_API_KEY
  BINANCE_API_SECRET
```

Create real values through the cluster's external secret manager or an equivalent controlled mechanism. Never commit them.

## 10. Binance Environment Separation

### Testnet

Use a Binance Spot Testnet account and Testnet credentials only. The allowed endpoint is:

```text
https://testnet.binance.vision
```

### Live

Use production credentials only after all promotion gates have passed. The production endpoint must be:

```text
https://api.binance.com
```

The execution environment guard rejects endpoint/environment mismatches.

## 11. Binance API Key Hardening

For each key:

- create a dedicated key for the platform;
- enable only required trading permissions;
- disable withdrawals;
- restrict IP addresses where operationally possible;
- do not reuse personal keys;
- rotate keys periodically and after suspected exposure;
- store keys only in a secret manager;
- never put secrets in logs, prompts, tickets or source code.

## 12. Deployment Sequence

### Research/Paper

1. Build and scan image.
2. Apply infrastructure.
3. Run migrations.
4. Deploy API.
5. Deploy workers.
6. Deploy dashboard.
7. Verify health.
8. Run unit/integration tests.
9. Run paper validation.

### Testnet

1. Provision Testnet-only secret.
2. Apply Testnet namespace/policies.
3. Deploy exact immutable image.
4. Verify endpoint is Testnet.
5. Run account/filter smoke test.
6. Run E2E order/fill/reconciliation tests.
7. Run failure suite.
8. Run soak test.

### Live

1. Confirm production-readiness evidence.
2. Confirm immutable strategy version and fingerprint.
3. Confirm risk-policy fingerprint.
4. Confirm two-person authorization.
5. Confirm approved capital allocation.
6. Confirm canary gate.
7. Confirm limited-live evidence before scaling.
8. Explicitly arm live only after all gates pass.
9. Monitor continuously.

## 13. Health Verification

Check API:

```bash
curl https://<api-host>/health
```

Check Kubernetes:

```bash
kubectl get pods -A
kubectl get events -A --sort-by=.lastTimestamp
```

Check deployment image:

```bash
kubectl -n <namespace> get deployment <name> -o jsonpath='{.spec.template.spec.containers[*].image}'
```

Record the deployed Git SHA in the release record.

## 14. Rollback

If a deployment is unhealthy:

1. Stop promotion/scaling.
2. Enable the kill switch if trading could be affected.
3. Halt the active promotion if necessary.
4. Preserve evidence and logs.
5. Roll back application workloads to the last known-good immutable image.
6. Do not blindly roll back database migrations; use a tested forward-fix strategy unless a database rollback procedure has been explicitly validated.
7. Reconcile exchange state.
8. Verify account, orders, fills, positions and balances.
9. Re-run health and regression tests.

## 15. Backups and Restore

Back up PostgreSQL according to business RPO/RTO requirements. At minimum test:

- database restore;
- application startup against restored data;
- promotion/audit record integrity;
- reconciliation state;
- outbox consistency.

A backup is not considered valid until a restore test succeeds.

## 16. CI/CD Gate

Every merge must pass the repository CI workflow. Production deployment should consume the exact commit that passed CI. Do not deploy untested local changes.

## 17. Release Record

For every deployment record:

```text
release_id
Git SHA
image digest
environment
operator
migration version
configuration version
strategy version, if applicable
risk-policy fingerprint
deployment timestamp
rollback target
verification result
```
