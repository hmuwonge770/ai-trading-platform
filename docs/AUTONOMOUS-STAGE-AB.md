# Autonomous Stage AB — Operational Alert Delivery

## Objective

Provide a credential-free operational alert delivery boundary for autonomous execution monitoring. The autonomy layer produces immutable alert contracts and delegates notification delivery to an application-owned sink.

## Five implementation phases

1. **Design & contract** — immutable alert, severity, delivery status, and sink contracts.
2. **Core implementation** — deterministic delivery with bounded recent-key deduplication.
3. **Safety/control integration** — delivery has no exchange, authorization, capital, or risk authority.
4. **Tests & failure scenarios** — cover successful delivery, duplicate suppression, delivery failure, retryability, bounded state, and invalid input.
5. **CI → merge → post-merge verification** — Stage AB is complete only after CI passes, the change is merged to `main`, and post-merge CI is green.

## Safety boundary

This stage does not contain Binance credentials, exchange clients, order operations, authorization, capital allocation, or risk-policy mutation. Delivery failures are isolated and reported as `BLOCKED`; failed alerts are not marked delivered, so a later retry remains possible.

The notification transport is deliberately injected through `OperationalAlertSink`. Production applications own credentials and external delivery configuration outside the autonomy decision plane.
