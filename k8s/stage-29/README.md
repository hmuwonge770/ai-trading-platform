# Stage 29 — Kubernetes Isolation

This stage defines the deployment boundary between research, paper, Testnet and live execution.

## Isolation model

- `trading-research`: no exchange credentials; default-deny ingress/egress.
- `trading-paper`: no exchange credentials; default-deny ingress/egress.
- `trading-testnet`: Testnet credentials only; default-deny networking.
- `trading-live`: Live credentials only; default-deny networking.
- `trading-monitoring`: reserved for observability components.

Every trading namespace has a dedicated ServiceAccount. Credential templates contain placeholders only and must be provisioned through a cluster secret manager rather than committed values.

## Fail-closed controls

The Kubernetes layer intentionally starts with deny-by-default policies. Application-level `EnvironmentGuard` remains authoritative for endpoint selection, while Kubernetes policies provide an independent blast-radius boundary. Testnet and live credentials are never placed in research or paper manifests.

The current NetworkPolicy set permits DNS only in the isolated namespaces. Environment-specific internet egress is deliberately not enabled by this stage until the cluster's CNI, egress gateway and audited destination controls are selected. This prevents a policy manifest from falsely claiming that an arbitrary Kubernetes cluster can enforce hostname-level Binance endpoint restrictions.

## Validation

Use a CNI that enforces NetworkPolicy and validate the rendered manifests with `kubectl apply --dry-run=server` in a target cluster. Then verify from each namespace that unauthorized cross-namespace and external connections are denied. Endpoint-specific egress should be enabled only through an audited egress gateway/firewall that can enforce the Binance Testnet versus production destination boundary.

No credentials, exchange requests or live orders are used by CI for this stage.
