# Stage 25 — Full Execution Integration

Stage 25 connects the persisted promotion authorization boundary to the deterministic execution service.

## Execution path

```text
OrderIntent
  -> persisted promotion authorization
  -> authorization expiry/status check
  -> strategy-version match
  -> risk-policy fingerprint match
  -> Binance environment guard
  -> independent RiskDecision approval
  -> ExecutionService
  -> exchange/simulator backend
```

## Controls

- Only an authorization whose promotion is `ACTIVE` and whose TTL has not expired can proceed.
- The authorization is bound to the exact strategy version on the order.
- The risk-policy fingerprint is bound to the authorization and must match at submission time.
- LIVE execution remains fail-closed unless explicitly armed.
- The execution service still requires an independent positive `RiskDecision`.
- Rejected authorization/risk/environment checks never invoke the execution backend.
- The AI researcher is not on the execution path and receives no exchange credentials.
- PostgreSQL is the source of truth for persisted promotion authorization; the execution store is read-only.

Stage 25 does not enable live trading by itself. Testnet E2E, failure/property testing, soak testing, and the later production authorization stages remain required.
