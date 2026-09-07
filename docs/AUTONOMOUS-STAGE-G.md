# Autonomous Stage G — Position & Portfolio Maintenance

Stage G adds deterministic maintenance of existing spot positions. It is an exit-safety layer, not an autonomous position opener.

## Flow

```text
Existing Position
    -> fresh quote validation
    -> stop-loss / take-profit policy
    -> HOLD or EXIT directive
    -> existing risk gate
    -> existing execution loop
```

## Controls

- Only existing positive positions are evaluated.
- The agent never creates a BUY/open-position directive.
- Future quotes are rejected.
- Stale quotes fail closed to HOLD rather than generating an exit from stale information.
- Stop-loss and take-profit thresholds are deterministic policy values.
- Any EXIT directive must still pass the autonomous risk engine and execution authorization.
- No exchange credentials or exchange calls exist in this agent.

## Verification

Unit tests cover stop-loss exit, take-profit exit, normal HOLD behavior, stale/future quote handling, and policy validation.
