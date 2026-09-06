# Stage 32 — Live Canary

Stage 32 is the controlled transition from approved promotion to a deliberately small live-canary allocation.

## Safety boundary

The canary controller accepts only an approved `LIVE_CANARY` promotion and a valid SHA-256 authorization hash. It never expands the approved capital allocation.

Activation additionally requires an immutable `CanaryGateReport` with every condition clean:

- zero reconciliation errors;
- zero unresolved unknown orders;
- zero balance/position mismatches;
- zero risk violations;
- zero critical execution errors;
- healthy trading account;
- fresh market data;
- closed circuit breaker;
- disabled kill switch.

A failed condition keeps the canary `ARMED` and cannot activate or scale it.

## Lifecycle

```text
DISARMED -> ARMED -> ACTIVE -> HALTED
             |          |
             +----------+
                  gate
```

`scale()` requires another clean gate report. Capital can only increase through the canary scaling operation; reductions use the separate reduction path planned by the promotion workflow.

## Operational rule

Stage 32 does not bypass Stage 31 authorization, environment isolation, risk approval, reconciliation, or the explicit live-arm requirement. It adds the canary-specific operational gate before activation and every scale-up.
