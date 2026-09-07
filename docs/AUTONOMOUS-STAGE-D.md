# Autonomous Stage D — AI Market-Regime & Signal Intelligence

Stage D adds an AI advisory layer to the continuous autonomous market loop without granting the model execution authority.

## Flow

```text
MarketSnapshot
    -> deterministic regime detection
    -> AI signal proposal
    -> deterministic validation
    -> bounded Decision
```

## Deterministic boundaries

- The AI provider receives market features and regime context only; no exchange credentials are exposed.
- AI output is typed and validated before it becomes a `Decision`.
- Signal symbols must match the market snapshot.
- Signals issued in the future are rejected.
- Signals older than the configured maximum age are rejected.
- Expired signals fail closed to `HOLD`.
- Confidence below the configured threshold fails closed to `HOLD`.
- A BUY proposal conflicting with a detected downtrend fails closed to `HOLD`.
- A SELL proposal conflicting with a detected uptrend fails closed to `HOLD`.
- Unknown regimes are rejected.
- No sizing, risk approval, exchange calls, or order submission occur in this stage.

## AI provider contract

`AISignalModel` is provider-neutral. An implementation may use an LLM or another model, but it must return `AISignalProposal`. The autonomous intelligence layer remains the trust boundary and treats the model response as untrusted input.

## Expiry

Every AI proposal carries `issued_at` and `expires_at`. This prevents a delayed model response from becoming a stale trading decision. The later risk/execution stages remain authoritative and may reject the resulting decision independently.

## Verification

Unit tests cover regime classification, valid model output, confidence and expiry handling, symbol mismatch, stale/future output, and directional regime conflicts.
