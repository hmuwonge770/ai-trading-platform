-- Stage 22 promotion / authorization schema.
-- PostgreSQL. IDs are UUIDs; monetary values use NUMERIC, never floating point.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS strategy_versions (
    id UUID PRIMARY KEY,
    strategy_id UUID NOT NULL,
    fingerprint CHAR(64) NOT NULL UNIQUE,
    configuration JSONB NOT NULL,
    frozen BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT strategy_versions_frozen_check CHECK (frozen = TRUE)
);

CREATE TABLE IF NOT EXISTS strategy_promotions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_version_id UUID NOT NULL REFERENCES strategy_versions(id),
    from_stage VARCHAR(32) NOT NULL,
    to_stage VARCHAR(32) NOT NULL,
    requested_by VARCHAR(255) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    required_approvals INTEGER NOT NULL DEFAULT 2,
    evidence_snapshot_hash CHAR(64) NOT NULL,
    max_capital NUMERIC(30,12) NOT NULL,
    max_position_value NUMERIC(30,12) NOT NULL,
    max_daily_loss NUMERIC(30,12) NOT NULL,
    max_orders_per_day INTEGER NOT NULL,
    allocation_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    activated_at TIMESTAMPTZ,
    halted_at TIMESTAMPTZ,
    CONSTRAINT strategy_promotions_live_target CHECK (to_stage IN ('live_canary','live_limited','live')),
    CONSTRAINT strategy_promotions_positive_limits CHECK (
        max_capital > 0 AND max_position_value > 0 AND max_position_value <= max_capital
        AND max_daily_loss > 0 AND max_daily_loss <= max_capital AND max_orders_per_day > 0
    )
);

CREATE INDEX IF NOT EXISTS idx_strategy_promotions_version_status
    ON strategy_promotions(strategy_version_id, status);

CREATE TABLE IF NOT EXISTS promotion_approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    promotion_id UUID NOT NULL REFERENCES strategy_promotions(id) ON DELETE CASCADE,
    approver_id VARCHAR(255) NOT NULL,
    role VARCHAR(32) NOT NULL,
    decision VARCHAR(16) NOT NULL,
    fingerprint CHAR(64) NOT NULL,
    capital_limit NUMERIC(30,12) NOT NULL,
    evidence_hash CHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT promotion_approvals_role CHECK (role IN ('risk_manager','admin','operations')),
    CONSTRAINT promotion_approvals_decision CHECK (decision IN ('approve','reject')),
    UNIQUE (promotion_id, approver_id)
);

CREATE INDEX IF NOT EXISTS idx_promotion_approvals_promotion
    ON promotion_approvals(promotion_id);

CREATE TABLE IF NOT EXISTS authorization_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    promotion_id UUID NOT NULL REFERENCES strategy_promotions(id),
    strategy_version_id UUID NOT NULL REFERENCES strategy_versions(id),
    strategy_fingerprint CHAR(64) NOT NULL,
    environment VARCHAR(32) NOT NULL,
    risk_policy_fingerprint CHAR(64) NOT NULL,
    evidence_snapshot_hash CHAR(64) NOT NULL,
    authorization_hash CHAR(64) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT authorization_snapshots_live_environment CHECK (
        environment IN ('live_canary','live_limited','live')
    )
);

CREATE INDEX IF NOT EXISTS idx_authorization_snapshots_active
    ON authorization_snapshots(strategy_version_id, environment, expires_at);

CREATE TABLE IF NOT EXISTS capital_allocations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_version_id UUID NOT NULL REFERENCES strategy_versions(id),
    environment VARCHAR(32) NOT NULL,
    max_capital NUMERIC(30,12) NOT NULL,
    max_position_value NUMERIC(30,12) NOT NULL,
    max_daily_loss NUMERIC(30,12) NOT NULL,
    max_orders_per_day INTEGER NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(strategy_version_id, environment),
    CONSTRAINT capital_allocations_limits CHECK (
        max_capital > 0 AND max_position_value > 0 AND max_position_value <= max_capital
        AND max_daily_loss > 0 AND max_daily_loss <= max_capital AND max_orders_per_day > 0
    )
);
