# Stage 32 Canary Checklist

Before activation, verify the promotion is approved and the authorization hash is bound to the exact frozen strategy version.

The canary gate must report:

- reconciliation errors = 0
- unresolved unknowns = 0
- balance/position mismatches = 0
- risk violations = 0
- critical execution errors = 0
- account healthy = true
- market data fresh = true
- circuit breaker open = false
- kill switch = false

If any condition fails, remain `ARMED` or halt the canary. Do not scale until a fresh clean gate report is available.
