# Autonomous Stage J — Paper Trading Orchestrator

## Purpose

Stage J connects the existing autonomous control, deterministic risk, execution, and recovery components into one **paper-only** orchestration boundary.

## Flow

1. Require `PAPER` mode.
2. Require the autonomous control plane to be `RUNNING` and permitted to operate.
3. Require the recovery engine not to be halted.
4. Evaluate the decision through the autonomous risk engine.
5. Submit only an approved intent through the existing execution abstraction.
6. Record execution success/failure through the bounded recovery engine.

## Safety boundary

The runner explicitly rejects `TESTNET` and `LIVE` modes. It does not own exchange credentials, create exchange clients, bypass the deterministic risk gateway, or submit directly to Binance.

A failed execution can consume the bounded recovery budget. Recovery halts are fail-closed and must follow the reconciliation/reset path before autonomous processing resumes.

## Live-trading rule

This stage does **not** authorize live trading. A future live adapter must be separately integrated behind the existing authorization, risk, reconciliation, promotion, and operational controls. The paper runner must remain paper-only.
