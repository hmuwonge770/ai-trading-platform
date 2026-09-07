# Autonomous Trading — Stage Z: Execution Observability

Stage Z adds an immutable, append-only audit contract for the controlled live runtime.

## Purpose

Every orchestration attempt can produce a deterministic, secret-free execution event containing:

- runtime mode and outcome;
- client order ID;
- strategy version and immutable strategy fingerprint;
- authorization hash;
- risk approval state;
- execution timestamp;
- safe rejection/blocking reasons; and
- exchange order ID when the injected adapter returns one.

The event ID is a SHA-256 digest of the canonical event payload. Replaying the same event data therefore produces the same event identity.

## Safety boundaries

- No Binance client or credential is stored in the audit layer.
- Secrets, API keys, and signatures are never recorded.
- Audit storage is an injected append-only sink; the autonomy package does not choose a database or mutate trading state.
- Disabled, preflight, dry-run, blocked, and duplicate paths cannot be represented as `submitted` events by the orchestrator.
- Audit recording does not approve promotions, renew authorization, change capital, alter risk policy, or bypass the kill switch.
- Exchange responses are reduced to the safe `orderId` field only.

## Integration

`AutonomousLiveRuntimeOrchestrator` accepts an optional `ExecutionAuditSink`. When supplied, it records one immutable `ExecutionAuditEvent` for each orchestration outcome. Existing runtime, authorization, risk, control-plane, adapter, and execution gates remain authoritative.

The default runtime posture remains disabled with execution disabled and the kill switch enabled.

## Next stage

The next stage should connect this append-only contract to the application's durable audit/event store and operational monitoring without moving credentials or execution authority into the autonomy layer.
