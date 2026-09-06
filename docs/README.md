# Documentation

This directory contains both **application user documentation** and **engineering/operations documentation** for the AI Trading Platform.

## For application users

1. [Application User Guide](APPLICATION-USER-GUIDE.md) — how to use the application, understand the dashboard, run research, evaluate strategies, use paper/Testnet environments, understand risk controls and operate the promotion lifecycle.
2. [User Manual](USER-MANUAL.md) — operational user manual covering the research-to-live workflow, daily checks and emergency controls.

The Application User Guide is the best starting point for someone who wants to understand **what the application does and how to use it**.

## For deployment and administrators

3. [Deployment Guide](DEPLOYMENT.md) — local Docker, production infrastructure, Kubernetes and release procedure.
4. [Configuration Reference](CONFIGURATION.md) — environment variables, endpoints, strategy/risk configuration and secret distribution.
5. [Security and Secrets](SECURITY-AND-SECRETS.md) — API keys, permissions, rotation and security boundaries.
6. [Operations Runbook](OPERATIONS-RUNBOOK.md) — incidents, reconciliation, kill switch, rollback and disaster recovery.

## Engineering and implementation reference

7. `stage-*.md` — detailed design and acceptance notes for individual implementation stages.

## Documentation rule

Keep the application guide focused on user workflows and observable behavior. Keep deployment, configuration, security and incident procedures in their dedicated documents.

Update the relevant documentation whenever an operational behavior, configuration variable, safety boundary, deployment process, user-facing workflow or promotion rule changes.

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
