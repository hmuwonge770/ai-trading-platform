# Stage 17 — Binance Spot Testnet

Stage 17 introduces the first exchange adapter, restricted to Binance Spot Testnet.

## Safety boundary

- Endpoint is hard-wired to `https://testnet.binance.vision`.
- Production Binance endpoints are rejected by configuration.
- API credentials belong only to the exchange adapter; research and AI components do not receive them.
- Unit tests use an HTTP mock transport and never contact Binance.
- The adapter signs authenticated REST requests with HMAC-SHA256.
- Market orders use the existing `ExecutionService` risk-approval boundary.

## Supported operations

- Testnet ping
- Signed account retrieval
- Signed market BUY/SELL orders
- Mapping Testnet order responses into the existing execution result contract

Live Binance production execution is intentionally outside Stage 17.
