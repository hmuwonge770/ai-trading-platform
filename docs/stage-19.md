# Stage 19 — Observability

Stage 19 exposes operational metrics for the control API and core trading boundaries.

## Metrics

The platform provides Prometheus-compatible counters, histograms, and gauges for:

- HTTP request totals and latency
- In-flight HTTP requests
- Risk decisions
- Execution outcomes
- Exchange adapter errors
- Accounting transactions

The HTTP middleware records the FastAPI route template rather than raw dynamic
URLs, keeping metric label cardinality bounded.

## Endpoint

`GET /metrics` returns the current Prometheus exposition format.

## Safety boundary

Observability contains operational facts only. Metrics do not expose API secrets,
request credentials, or arbitrary request payloads, and metrics cannot authorize
or submit trading orders.
