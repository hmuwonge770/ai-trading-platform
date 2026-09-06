from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from packages.database.models import Experiment, Job, JobStatus, MarketCandle, ResearchSession, Strategy, StrategyVersion


class ResearchSessionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, name: str, objective: str, config: dict | None = None) -> ResearchSession:
        session = ResearchSession(name=name, objective=objective, config=config or {})
        self.db.add(session)
        self.db.flush()
        return session

    def get(self, session_id: uuid.UUID) -> ResearchSession | None:
        return self.db.get(ResearchSession, session_id)


class StrategyRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, name: str, strategy_family: str, description: str | None = None) -> Strategy:
        strategy = Strategy(name=name, strategy_family=strategy_family, description=description)
        self.db.add(strategy)
        self.db.flush()
        return strategy

    def next_version(self, strategy_id: uuid.UUID) -> int:
        versions = self.db.scalars(select(StrategyVersion.version).where(StrategyVersion.strategy_id == strategy_id)).all()
        return (max(versions) + 1) if versions else 1

    def create_version(self, strategy_id: uuid.UUID, config: dict, fingerprint: str, hypothesis: str | None = None, parent_experiment_id: uuid.UUID | None = None, generation: int = 0) -> StrategyVersion:
        version = StrategyVersion(
            strategy_id=strategy_id,
            version=self.next_version(strategy_id),
            config=config,
            fingerprint=fingerprint,
            hypothesis=hypothesis,
            parent_experiment_id=parent_experiment_id,
            generation=generation,
        )
        self.db.add(version)
        self.db.flush()
        return version


class ExperimentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, session_id: uuid.UUID, strategy_version_id: uuid.UUID | None = None, parameters: dict | None = None, dataset_config: dict | None = None) -> Experiment:
        experiment = Experiment(session_id=session_id, strategy_version_id=strategy_version_id, parameters=parameters or {}, dataset_config=dataset_config or {})
        self.db.add(experiment)
        self.db.flush()
        return experiment

    def get(self, experiment_id: uuid.UUID) -> Experiment | None:
        return self.db.get(Experiment, experiment_id)


class MarketCandleRepository:
    def __init__(self, db: Session):
        self.db = db

    def upsert(self, candles: list[dict]) -> int:
        if not candles:
            return 0
        stmt = insert(MarketCandle).values(candles)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_market_candles_symbol_timeframe_open",
            set_={
                "close_time": stmt.excluded.close_time,
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "volume": stmt.excluded.volume,
                "quote_volume": stmt.excluded.quote_volume,
                "trade_count": stmt.excluded.trade_count,
            },
        )
        result = self.db.execute(stmt)
        self.db.flush()
        return result.rowcount

    def latest(self, symbol: str, timeframe: str, limit: int = 200) -> list[MarketCandle]:
        stmt = select(MarketCandle).where(MarketCandle.symbol == symbol, MarketCandle.timeframe == timeframe).order_by(MarketCandle.open_time.desc()).limit(limit)
        return list(reversed(self.db.scalars(stmt).all()))


class JobRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, job_type: str, payload: dict, session_id: uuid.UUID | None = None, experiment_id: uuid.UUID | None = None, max_attempts: int = 3) -> Job:
        job = Job(job_type=job_type, payload=payload, session_id=session_id, experiment_id=experiment_id, max_attempts=max_attempts)
        self.db.add(job)
        self.db.flush()
        return job

    def get(self, job_id: uuid.UUID) -> Job | None:
        return self.db.get(Job, job_id)
