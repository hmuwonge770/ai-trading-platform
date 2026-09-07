# AI Trading Platform — Security, Keys and Secrets

## 1. Security Boundary

The most important architectural rule is separation of authority:

```text
AI → research suggestions only
Deterministic software → validation/risk/execution
Humans → live capital authorization
```

No AI prompt should contain exchange secrets. No research workload should have live exchange credentials.

## 2. Secret Inventory

| Secret | Where it belongs | Never expose to |
|---|---|---|
| `OPENAI_API_KEY` | AI research workload secret store | source code/logs/prompts |
| `BINANCE_API_KEY` | environment-specific secret store | AI/research/testnet when live key |
| `BINANCE_API_SECRET` | environment-specific secret store | AI/research/logs |
| PostgreSQL password | DB/application secret store | Git/logs |
| RabbitMQ password | broker secret store | Git/logs |
| Redis password | Redis/application secret store | Git/logs |
| Kubernetes tokens | cluster secret mechanism | application logs |

## 3. Binance Keys

Create dedicated keys for this platform. Use separate credentials for Testnet and Live.

Recommended restrictions:

- trading permission only when required;
- withdrawals disabled;
- IP allow-list where practical;
- no unnecessary account permissions;
- rotate after personnel/access changes or suspected exposure.

The repository's Kubernetes template uses placeholder values only and explicitly states that real secret values must never be committed.

## 4. Key Installation

Use a managed secret system such as a cloud secret manager, Vault or an external-secrets controller.

For Kubernetes, the intended logical secrets are:

```text
trading-testnet / testnet-binance
trading-live    / live-binance
```

Each contains:

```text
BINANCE_API_KEY
BINANCE_API_SECRET
```

The application receives the values at runtime. They should never appear in deployment manifests, Dockerfiles or Git history.

## 5. OpenAI Key

Set `OPENAI_API_KEY` only in workloads that require AI research. Keep the research model configurable but keep execution authority outside the AI process.

If a provider key is exposed:

1. revoke/rotate it;
2. inspect logs and CI history;
3. remove the exposure from future artifacts;
4. review provider usage;
5. record the incident.

## 6. GitHub Secrets

CI/CD secrets should be configured as GitHub Actions secrets or environment-scoped secrets. Never put a production credential in workflow YAML.

Use environment protections for production deployments and require the appropriate human approvals.

## 7. Secret Scanning

Before every release:

```text
scan repository
scan Docker image
scan deployment manifests
scan CI configuration
review recent commits
```

If a secret is discovered, assume compromise until proven otherwise. Removing the text from the latest commit does not invalidate the secret; rotate it.

## 8. Network Security

Production components should use private networks wherever possible. Expose only required public endpoints.

Recommended boundaries:

```text
Internet
   |
 TLS / authenticated edge
   |
 Laravel / API
   |
 private application network
   +---- PostgreSQL
   +---- Redis
   +---- RabbitMQ
   +---- workers
```

Exchange egress should be explicitly restricted by environment.

## 9. Kubernetes Security

Use:

- separate namespaces;
- least-privilege service accounts;
- NetworkPolicies;
- resource limits;
- read-only filesystems where compatible;
- non-root containers where compatible;
- external secrets;
- image pinning/digests;
- admission/security scanning.

Research must not be able to route to the live namespace or read live secrets.

## 10. TLS

Use TLS for external APIs and production internal connections where supported. Never disable certificate verification to fix a connectivity problem.

## 11. Auditability

Record operator actions, promotion approvals, authorization snapshots, gate evidence, deployment versions and incident actions. Do not record secret values.

## 12. Access Roles

Live promotion requires distinct human authority. The implementation requires the appropriate Risk Manager and Admin approvals and prevents the requester from approving their own request.

Grant operators only the permissions required for their role.

## 13. Credential Rotation Runbook

```text
Prepare new credential
→ store in secret manager
→ deploy/reload
→ smoke test
→ verify reconciliation
→ revoke old credential
→ document rotation
```

For live rotation, use a tested controlled procedure and stop new orders if continuity cannot be proven.

## 14. Lost or Exposed Credential

If a Binance key is exposed:

1. immediately disable/revoke the key at Binance;
2. engage the kill switch;
3. halt active promotion;
4. inspect recent account/order activity;
5. reconcile balances, orders and fills;
6. rotate credentials;
7. inspect Git/CI/log exposure;
8. patch the root cause;
9. rerun security and integration tests;
10. require fresh authorization before live activity resumes.

## 15. Security Do-Not List

Never:

- commit `.env` files containing real secrets;
- paste secrets into issue comments;
- paste secrets into AI chats;
- log authorization headers or API secrets;
- bake secrets into Docker images;
- put secrets in Kubernetes ConfigMaps;
- reuse live keys in Testnet;
- enable Binance withdrawals for the bot;
- bypass environment guards;
- disable TLS verification;
- manually edit authorization hashes;
- reuse an authorization after a material configuration change.
