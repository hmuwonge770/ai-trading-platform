from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.database.base import Base


class ResearchSessionStatus(str, enum.Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class StrategyStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    RETIRED = "retired"


class ExperimentStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DEAD = "dead"


class ResearchSession(Base):
    __tablename__ = "research_sessions"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    objective: Mapped[str] = mapped_column(Text)
    status: Mapped[ResearchSessionStatus] = mapped_column(Enum(ResearchSessionStatus, name="research_session_status"), default=ResearchSessionStatus.CREATED)
    config: Mapped[dict] = mapped_column(JSONB, default=lambda: {})
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    experiments: Mapped[list[Experiment]] = relationship(back_populates="session")
    hypotheses: Mapped[list[ResearchHypothesis]] = relationship(back_populates="session")


class Strategy(Base):
    __tablename__ = "strategies"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[StrategyStatus] = mapped_column(Enum(StrategyStatus, name="strategy_status"), default=StrategyStatus.DRAFT)
    strategy_family: Mapped[str] = mapped_column(String(100), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    versions: Mapped[list[StrategyVersion]] = relationship(back_populates="strategy")


class StrategyVersion(Base):
    __tablename__ = "strategy_versions"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    strategy_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("strategies.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    config: Mapped[dict] = mapped_column(JSONB)
    hypothesis: Mapped[str | None] = mapped_column(Text)
    parent_experiment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("experiments.id", ondelete="SET NULL"))
    generation: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    strategy: Mapped[Strategy] = relationship(back_populates="versions", foreign_keys=[strategy_id])
    __table_args__ = (UniqueConstraint("strategy_id", "version", name="uq_strategy_versions_strategy_version"),)


class Experiment(Base):
    __tablename__ = "experiments"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("research_sessions.id", ondelete="CASCADE"), index=True)
    strategy_version_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("strategy_versions.id", ondelete="SET NULL"))
    status: Mapped[ExperimentStatus] = mapped_column(Enum(ExperimentStatus, name="experiment_status"), default=ExperimentStatus.QUEUED)
    parameters: Mapped[dict] = mapped_column(JSONB, default=lambda: {})
    dataset_config: Mapped[dict] = mapped_column(JSONB, default=lambda: {})
    experiment_fingerprint: Mapped[str | None] = mapped_column(String(64), unique=True)
    engine_version: Mapped[str | None] = mapped_column(String(50))
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    session: Mapped[ResearchSession] = relationship(back_populates="experiments")
    result: Mapped[BacktestResult | None] = relationship(back_populates="experiment", uselist=False)
    reviews: Mapped[list[AIReview]] = relationship(back_populates="experiment")


class BacktestResult(Base):
    __tablename__ = "backtest_results"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    experiment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"), unique=True)
    metrics: Mapped[dict] = mapped_column(JSONB)
    equity_curve: Mapped[dict] = mapped_column(JSONB, default=lambda: {})
    trade_count: Mapped[int] = mapped_column(Integer, default=0)
    total_return: Mapped[Decimal] = mapped_column(Numeric(24, 12), default=Decimal("0"))
    max_drawdown: Mapped[Decimal] = mapped_column(Numeric(24, 12), default=Decimal("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    experiment: Mapped[Experiment] = relationship(back_populates="result")


class AIReview(Base):
    __tablename__ = "ai_reviews"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    experiment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"), index=True)
    model: Mapped[str] = mapped_column(String(100))
    review_type: Mapped[str] = mapped_column(String(50))
    decision: Mapped[str] = mapped_column(String(50))
    reasoning: Mapped[str] = mapped_column(Text)
    structured_output: Mapped[dict] = mapped_column(JSONB, default=lambda: {})
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    experiment: Mapped[Experiment] = relationship(back_populates="reviews")


class ResearchHypothesis(Base):
    __tablename__ = "research_hypotheses"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("research_sessions.id", ondelete="CASCADE"), index=True)
    statement: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="proposed")
    extra_metadata: Mapped[dict] = mapped_column("metadata", JSONB, default=lambda: {})
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    session: Mapped[ResearchSession] = relationship(back_populates="hypotheses")


class MarketCandle(Base):
    __tablename__ = "market_candles"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32))
    timeframe: Mapped[str] = mapped_column(String(16))
    open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    close_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    open: Mapped[Decimal] = mapped_column(Numeric(30, 12))
    high: Mapped[Decimal] = mapped_column(Numeric(30, 12))
    low: Mapped[Decimal] = mapped_column(Numeric(30, 12))
    close: Mapped[Decimal] = mapped_column(Numeric(30, 12))
    volume: Mapped[Decimal] = mapped_column(Numeric(30, 12))
    quote_volume: Mapped[Decimal] = mapped_column(Numeric(30, 12))
    trade_count: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        UniqueConstraint("symbol", "timeframe", "open_time", name="uq_market_candles_symbol_timeframe_open"),
        Index("ix_market_candles_lookup", "symbol", "timeframe", "open_time"),
    )


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    job_type: Mapped[str] = mapped_column(String(100), index=True)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus, name="job_status"), default=JobStatus.PENDING, index=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("research_sessions.id", ondelete="SET NULL"))
    experiment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("experiments.id", ondelete="SET NULL"))
    payload: Mapped[dict] = mapped_column(JSONB, default=lambda: {})
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
