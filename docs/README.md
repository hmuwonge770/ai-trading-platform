# Documentation

This directory contains the operational documentation for the AI Trading Platform.

## Start here

1. [User Manual](USER-MANUAL.md) — day-to-day usage, research, paper, testnet and promotion workflow.
2. [Deployment Guide](DEPLOYMENT.md) — local Docker, production infrastructure, Kubernetes and release procedure.
3. [Configuration Reference](CONFIGURATION.md) — environment variables, endpoints, strategy/risk configuration and secret distribution.
4. [Security and Secrets](SECURITY-AND-SECRETS.md) — API keys, permissions, rotation and security boundaries.
5. [Operations Runbook](OPERATIONS-RUNBOOK.md) — incidents, reconciliation, kill switch, rollback and disaster recovery.
6. `stage-*.md` — detailed design and acceptance notes for individual implementation stages.

## Documentation rule

Update the relevant documentation whenever an operational behavior, configuration variable, safety boundary, deployment process or promotion rule changes.

Never document real secret values. Use placeholders and secret-manager references.

## Production quick reference

```text
CI green
  ↓
Immutable image / Git SHA
  ↓
Infrastructure healthy
  ↓
Migrations complete
  ↓
API + workers healthy
  ↓
Reconciliation healthy
  ↓
Environment/endpoint verified
  ↓
Strategy + risk fingerprints verified
  ↓
Promotion gates
  ↓
Human authorization
  ↓
Canary
  ↓
Limited Live
  ↓
Full Live
```

**If any gate fails, stop and investigate. Do not bypass it.**
