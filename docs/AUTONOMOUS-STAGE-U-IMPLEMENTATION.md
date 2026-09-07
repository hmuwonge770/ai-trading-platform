# Stage U Implementation Notes

Stage U adds a deterministic live execution handoff without adding a live exchange integration.

## Components

- `packages/autonomy/live_execution.py` — guarded boundary and injected submitter protocol.
- `tests/unit/test_autonomous_live_execution.py` — authorization, risk, control, strategy identity, duplicate, environment, and submitter-failure coverage.
- `docs/AUTONOMOUS-STAGE-U.md` — safety contract and operational posture.

## Design

The boundary is intentionally capability-based. The repository does not create or discover an exchange client here. A future adapter must be supplied by the runtime and remains responsible for exchange-specific authentication and transport.

The boundary accepts only an immutable authorization handoff and an already approved `AutonomousRiskResult`. It verifies live mode, runnable control state, live promotion environment, strategy identity, and client-order uniqueness before delegation.

This is a handoff contract, not a live-trading activation mechanism.
