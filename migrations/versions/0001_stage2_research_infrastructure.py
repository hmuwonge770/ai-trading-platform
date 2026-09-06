"""stage 2 research infrastructure

Revision ID: 0001_stage2
Revises:
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_stage2"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    for name, values in {
        "research_session_status": [
            "created", "running", "paused", "completed", "failed", "canceled"
        ],
        "strategy_status": ["draft", "active", "retired"],
        "experiment_status": [
            "queued", "running", "completed", "failed", "canceled"
        ],
        "job_status": ["pending", "running", "succeeded", "failed", "dead"],
    }.items():
        sa.Enum(*values, name=name).create(bind, checkfirst=True)

    op.create_table(
        "research_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column(
            "status", sa.Enum(name="research_session_status"), nullable=False
        ),
        sa.Column("config", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_table(
        "strategies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("status", sa.Enum(name="strategy_status"), nullable=False),
        sa.Column("strategy_family", sa.String(100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_strategies_strategy_family", "strategies", ["strategy_family"])

    # Created before strategy_versions so the two tables can form a lineage cycle.
    op.create_table(
        "experiments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("research_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("strategy_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.Enum(name="experiment_status"), nullable=False),
        sa.Column("parameters", postgresql.JSONB(), nullable=False),
        sa.Column("dataset_config", postgresql.JSONB(), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_experiments_session_id", "experiments", ["session_id"])

    op.create_table(
        "strategy_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "strategy_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("strategies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "fingerprint", sa.String(64), nullable=False, unique=True
        ),
        sa.Column("config", postgresql.JSONB(), nullable=False),
        sa.Column("hypothesis", sa.Text()),
        sa.Column(
            "parent_experiment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("experiments.id", ondelete="SET NULL"),
        ),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "strategy_id", "version", name="uq_strategy_versions_strategy_version"
        ),
    )
    op.create_index("ix_strategy_versions_strategy_id", "strategy_versions", ["strategy_id"])
    op.create_foreign_key(
        "fk_experiments_strategy_version",
        "experiments",
        "strategy_versions",
        ["strategy_version_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "backtest_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "experiment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("experiments.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("metrics", postgresql.JSONB(), nullable=False),
        sa.Column("equity_curve", postgresql.JSONB(), nullable=False),
        sa.Column("trade_count", sa.Integer(), nullable=False),
        sa.Column("total_return", sa.Numeric(24, 12), nullable=False),
        sa.Column("max_drawdown", sa.Numeric(24, 12), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_table(
        "ai_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "experiment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("experiments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("review_type", sa.String(50), nullable=False),
        sa.Column("decision", sa.String(50), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("structured_output", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_ai_reviews_experiment_id", "ai_reviews", ["experiment_id"])
    op.create_table(
        "research_hypotheses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("research_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text()),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_research_hypotheses_session_id", "research_hypotheses", ["session_id"]
    )
    op.create_table(
        "market_candles",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("timeframe", sa.String(16), nullable=False),
        sa.Column("open_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("close_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(30, 12), nullable=False),
        sa.Column("high", sa.Numeric(30, 12), nullable=False),
        sa.Column("low", sa.Numeric(30, 12), nullable=False),
        sa.Column("close", sa.Numeric(30, 12), nullable=False),
        sa.Column("volume", sa.Numeric(30, 12), nullable=False),
        sa.Column("quote_volume", sa.Numeric(30, 12), nullable=False),
        sa.Column("trade_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "symbol", "timeframe", "open_time",
            name="uq_market_candles_symbol_timeframe_open",
        ),
    )
    op.create_index(
        "ix_market_candles_lookup",
        "market_candles",
        ["symbol", "timeframe", "open_time"],
    )
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_type", sa.String(100), nullable=False),
        sa.Column("status", sa.Enum(name="job_status"), nullable=False),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("research_sessions.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "experiment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("experiments.id", ondelete="SET NULL"),
        ),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_jobs_job_type", "jobs", ["job_type"])
    op.create_index("ix_jobs_status", "jobs", ["status"])


def downgrade() -> None:
    for table in [
        "jobs",
        "market_candles",
        "research_hypotheses",
        "ai_reviews",
        "backtest_results",
    ]:
        op.drop_table(table)
    op.drop_constraint(
        "fk_experiments_strategy_version", "experiments", type_="foreignkey"
    )
    op.drop_table("strategy_versions")
    op.drop_table("experiments")
    op.drop_table("strategies")
    op.drop_table("research_sessions")
    bind = op.get_bind()
    for name in [
        "job_status", "experiment_status", "strategy_status", "research_session_status"
    ]:
        sa.Enum(name=name).drop(bind, checkfirst=True)
