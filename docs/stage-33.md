# Stage 33 — Limited Live

Stage 33 introduces a fail-closed limited-live promotion controller after the live-canary stage.

## Controls

- Requires a promotion explicitly targeting `LIVE_LIMITED`.
- Requires the promotion to be fully approved before arming.
- Binds the controller to a 64-character authorization hash.
- Enforces capital, position, daily-loss, and daily-order limits against the approved allocation.
- Requires a clean canary/reconciliation gate before activation.
- Supports an explicit halt and disarm path.
- Scaling is permitted only while active and only with a fresh clean gate.
- Every scale operation requires a fresh authorization hash; reusing the prior authorization is rejected.
- A scale-up cannot exceed the limits authorized by the promotion allocation.

## Safety boundary

This stage defines promotion state and safety gates only. It does not grant exchange credentials, bypass risk controls, or submit live Binance orders. Production execution remains behind the existing authorization, environment, risk, reconciliation, and kill-switch controls.

## Required operational evidence

Before scaling limited-live capital, operators should record the clean reconciliation/risk/account/market-data evidence represented by `CanaryGateReport` and issue a new approved authorization for the new limits.
