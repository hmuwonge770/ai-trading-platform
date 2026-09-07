# Autonomous Stage AA — Execution Monitoring and Alerting

## Purpose

Stage AA adds a deterministic, read-only health monitor around autonomous execution. It consumes the existing secret-free execution audit events and application-supplied runtime health state.

## Signals

The monitor detects:

- invalid or expired live authorization;
- unhealthy live exchange adapter;
- unhealthy reconciliation;
- unhealthy accounting;
- active kill switch;
- repeated execution blocks;
- repeated duplicate-order suppression.

Critical control, authorization, adapter, reconciliation, accounting, and kill-switch conditions produce `CRITICAL` alerts. Repeated operational patterns produce bounded `WARNING` alerts.

## Safety

The monitor cannot submit, cancel, amend, or retry orders. It cannot approve or renew authorization, change capital, alter risk policy, disable the kill switch, or activate a promotion. Alerts are append-only through an injected application sink.

No exchange credentials or private exchange responses are accepted by the monitor. The audit layer remains the only execution evidence input.

## Fail-closed posture

Monitoring does not make an unsafe runtime safe. A `CRITICAL` report is an explicit signal that the surrounding application must keep execution stopped. Existing authorization, risk, runtime, adapter, reconciliation, accounting, and kill-switch gates remain authoritative.

## Next stage

Later stages may integrate alerts with operational dashboards and notification channels. Such integrations must remain observational and must not bypass the execution safety boundaries.
