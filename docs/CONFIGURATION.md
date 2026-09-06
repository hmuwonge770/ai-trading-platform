# AI Trading Platform — Configuration Reference

This document is the authoritative operational checklist for configuration. Keep actual secret values outside Git.

## 1. Base Environment

Current repository defaults in `.env.example`:

```env
APP_ENV=local
DATABASE_URL=postgresql+psycopg://trading:trading_dev_password@localhost:5433/trading_research
REDIS_URL=redis://localhost:6379/0
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
BINANCE_BASE_URL=https://api.binance.com
OPENAI_API_KEY=
OPENAI_RESEARCH_MODEL=gpt-5.6-luna
TRADING_ENVIRONMENT=paper
TRADING_ENABLED=false
TRADING_KILL_SWITCH=true
```

These are development/example values. Production must use managed services, authenticated connections and environment-specific credentials.

## 2. Configuration Classes

### Application

| Variable | Purpose | Safe default |
|---|---|---|
| `APP_ENV` | Runtime environment label | `local` |
| `OPENAI_RESEARCH_MODEL` | Model used by research workflows | repository default |

### Database

| Variable | Purpose | Production requirement |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection | TLS, private network, secret credentials |

Use a dedicated database role. Never use a superuser from the application.

### Redis

`REDIS_URL` points to Redis. Production should use authentication/TLS and private networking where supported.

### RabbitMQ

`RABBITMQ_URL` points to the broker. Production should use a dedicated application user, TLS and restricted management access. Do not use `guest` for production.

## 3. AI Provider Key

`OPENAI_API_KEY` is used by the AI research plane.

Rules:

- inject it from a secret manager;
- do not commit it;
- do not print it;
- do not send Binance credentials to the AI provider;
- use the least provider permissions available;
- rotate on exposure.

The AI layer can generate research output but must not become the authority for execution or promotion.

## 4. Binance Configuration

### Endpoint

`BINANCE_BASE_URL` identifies the Binance API environment.

Allowed values are controlled by the trading environment guard:

```text
TESTNET → https://testnet.binance.vision
LIVE    → https://api.binance.com
```

Paper mode must not submit Binance orders.

### Credentials

Credentials are intentionally not present in `.env.example`.

Use:

```text
BINANCE_API_KEY
BINANCE_API_SECRET
```

These should exist only in the environment that requires them. Research and paper workloads should not receive exchange credentials.

## 5. Trading Safety Configuration

```env
TRADING_ENVIRONMENT=paper
TRADING_ENABLED=false
TRADING_KILL_SWITCH=true
```

Interpretation:

- `paper` means simulated operation;
- `false` prevents trading activation;
- `true` means the emergency kill switch is engaged.

Changing these variables is not a substitute for promotion authorization. Live execution remains protected by deterministic promotion, authorization, risk, environment and full-live gates.

## 6. Risk Policy

Risk policy must be versioned and fingerprinted. Material changes require fresh authorization.

The policy hierarchy is:

```text
Global → Environment → Strategy → Symbol → Order
```

Typical policy dimensions include:

- maximum position size;
- total exposure;
- daily loss;
- maximum drawdown;
- number of open positions;
- order-rate limits;
- stale-market-data limits;
- circuit-breaker thresholds.

Do not copy illustrative values from historical documentation into production without an explicit risk review.

## 7. Strategy Configuration

A strategy should identify:

```text
family
hypothesis
symbol
timeframe
indicators
entry_conditions
exit_conditions
risk
```

The system computes a deterministic strategy fingerprint. Live authorization must reference the exact immutable strategy version and fingerprint.

## 8. Promotion Configuration

Every live authorization must bind:

```text
promotion_id
strategy_version_id
strategy_fingerprint
risk_policy_fingerprint
capital allocation
maximum position
maximum daily loss
maximum orders/day
evidence snapshot hash
authorization hash
approvers
```

Changing a material field invalidates the authorization.

## 9. Secret Distribution Matrix

| Secret/config | Research | Paper | Testnet | Live |
|---|---:|---:|---:|---:|
| AI provider key | Yes | Optional | Optional | Optional |
| Testnet Binance key | No | No | Yes | No |
| Live Binance key | No | No | No | Yes |
| DB credentials | Required | Required | Required | Required |
| RabbitMQ credentials | Required | Required | Required | Required |
| Redis credentials | Required | Required | Required | Required |

The matrix is a security boundary, not merely documentation.

## 10. Kubernetes Secret Names

The stage-29 template defines:

```text
Secret: testnet-binance
Namespace: trading-testnet

Secret: live-binance
Namespace: trading-live
```

Each contains:

```text
BINANCE_API_KEY
BINANCE_API_SECRET
```

Create these with an external secret manager. Never replace `REPLACE_ME` in Git.

## 11. Rotation Procedure

1. Create a new credential.
2. Restrict it to the intended environment/IPs/permissions.
3. Store it in the secret manager.
4. Deploy/reload the affected workload.
5. Run the appropriate account/connectivity smoke test.
6. Verify reconciliation and monitoring.
7. Revoke the old credential.
8. Record the rotation without recording the secret value.

For live credentials, stop new promotions and consider halting live execution during rotation unless the deployment has a tested zero-downtime credential rotation procedure.

## 12. Configuration Validation

Before enabling an environment, verify:

```text
environment ↔ endpoint
credentials ↔ environment
strategy version ↔ fingerprint
authorization ↔ strategy/risk/capital
gate ↔ current evidence
```

Any mismatch must fail closed.

## 13. Never Store

Never place these in Git, Docker images, AI prompts or logs:

- Binance API secrets;
- OpenAI API keys;
- database passwords;
- RabbitMQ passwords;
- Redis passwords;
- Kubernetes service-account tokens;
- private keys;
- recovery codes.

Use placeholders and secret-manager references instead.
