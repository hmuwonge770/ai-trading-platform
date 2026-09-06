# AI Trading Platform

Research-first, risk-controlled quantitative trading platform.

## Stage 22: Promotion & Live Authorization

This repository currently contains the initial promotion/authorization foundation. It is deliberately fail-closed: creating an approval does not enable live trading by itself.

### Principles

- AI performs research; deterministic services enforce trading policy.
- Strategy versions are immutable and fingerprinted.
- Live promotion requires independent human approvals.
- Capital allocation is explicit and bounded.
- Authorization is bound to the exact strategy fingerprint, risk policy, capital allocation, and approvals.
- Deployment environment and exchange endpoint are validated before execution.
- Live trading remains disarmed by default.

## Layout

```text
apps/
  control_api/
packages/
  promotion/
  trading/
  risk/
  exchange/
migrations/
tests/
```

## Run tests

```bash
python -m pytest
```
