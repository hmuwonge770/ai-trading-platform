# Autonomous Trading — Stage W

## Credential-Isolated Live Adapter

Stage W establishes the concrete Binance production adapter outside the autonomy
package. Credentials are injected into `packages/execution/binance_live.py` and
are never passed to AI decision logic or stored in autonomous state.

### Controls

- Production endpoint is fixed to `https://api.binance.com`.
- Testnet and sandbox endpoints cannot be configured through the live adapter.
- Credentials are supplied by the deployment environment rather than source.
- Adapter healthcheck is required before runtime use.
- The autonomy execution boundary remains responsible for authorization, LIVE
  control state, deterministic risk approval, strategy identity, and order-ID
  deduplication.
- No automatic capital allocation, authorization, risk-policy changes, or
  kill-switch changes are performed here.

### Scope

The adapter implements the exchange transport capability and a signed market
order request, but this stage does **not** enable live trading by default and
contains no autonomous startup path. A deployment must explicitly wire the
adapter behind all existing gates.

The default application posture remains fail closed.
