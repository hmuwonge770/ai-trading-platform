# Stage 34 — Full Live

Stage 34 is the final promotion boundary before full live trading. It is deterministic and fail-closed.

## Required gates

A full-live gate passes only when all of the following are true:

- immutable/frozen strategy version is unchanged
- strategy version ID and fingerprint exactly match the promotion and authorization
- risk-policy fingerprint exactly matches the authorization
- approved capital exactly matches the promotion and authorization
- canary stage passed
- limited-live stage passed
- account health passed
- reconciliation health passed
- circuit breaker is closed
- kill switch is deliberately disabled
- explicit live arm is present
- production credentials are configured
- production endpoint is exactly `https://api.binance.com`

Any failed condition blocks activation and is returned in the gate report.

## Safety boundary

`FullLiveGate` validates evidence and configuration only. It does not retrieve secrets, expose credentials, or submit exchange orders. `FullLiveController` can activate only after a passed gate and binds the active lifecycle to the exact authorization hash.

Changing the strategy version, strategy fingerprint, risk policy, capital, or any required operational gate must cause full-live activation to fail until a new approved authorization and clean evidence set are produced.
