# Stage 26 — Binance Spot Testnet E2E

Stage 26 exercises the execution path through the Stage 17 Binance Spot Testnet adapter and Stage 16 execution service.

## Flow

1. Validate the adapter is configured for `https://testnet.binance.vision`.
2. Ping Binance Spot Testnet.
3. Authenticate against the Spot Testnet account endpoint.
4. Require an independently approved deterministic `RiskDecision`.
5. Submit the order through `ExecutionService`.
6. Execute through `BinanceSpotTestnetClient` and map the exchange response into the execution contract.

## Safety boundary

- Production Binance endpoints are rejected by the existing Stage 17 configuration and environment guard.
- The E2E harness does not contain or load credentials itself.
- CI uses `httpx.MockTransport`, so CI never submits an exchange order.
- The real adapter can be supplied with Spot Testnet credentials for an operator-controlled smoke run.
- Live promotion authorization remains separate and cannot be bypassed by this testnet harness.
- An order cannot reach the adapter without an independent risk approval.

## Verification

`tests/unit/test_stage26_testnet_e2e.py` verifies the complete ping → account → risk gate → order flow, signature presence, order mapping, risk rejection, and production-endpoint rejection without contacting Binance.
