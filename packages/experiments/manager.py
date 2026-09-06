from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from packages.database.models import (
    BacktestResult,
    Experiment,
    ExperimentStatus,
    Strategy,
    StrategyStatus,
    StrategyVersion,
)
from packages.experiments.fingerprint import experiment_fingerprint
from packages.experiments.lineage import (
    AntiOverfittingPolicy,
    lineage_fingerprint,
    validate_parent_lineage,
)
from packages.experiments.models import ExperimentConfig
from packages.strategies.fingerprint import strategy_fingerprint


class DuplicateExperimentError(ValueError):
    """Raised when the exact same experiment has already been recorded."""


class ExperimentManager:
    """Persist immutable experiment inputs, lineage, and deterministic results."""

    def __init__(self, policy: AntiOverfittingPolicy | None = None) -> None:
        self.policy = policy or AntiOverfittingPolicy()

    def create(
        self,
        db: Session,
        config: ExperimentConfig,
        *,
        dataset_fingerprint: str | None = None,
    ) -> Experiment:
        session_id = uuid.UUID(config.session_id)
        parent = None
        if config.parent_experiment_id:
            parent = db.get(Experiment, uuid.UUID(config.parent_experiment_id))
            if parent is None:
                raise ValueError("parent experiment not found")

        validate_parent_lineage(
            session_id=session_id,
            generation=config.generation,
            parent_experiment_id=(uuid.UUID(config.parent_experiment_id) if config.parent_experiment_id else None),
            parent_session_id=parent.session_id if parent else None,
            parent_generation=parent.generation if parent else None,
        )

        existing_count = db.scalar(
            select(func.count()).select_from(Experiment).where(Experiment.session_id == session_id)
        ) or 0
        self.policy.validate_budget(
            existing_experiments=int(existing_count), generation=config.generation
        )

        experiment_fp = experiment_fingerprint(config, dataset_fingerprint)
        existing = db.scalar(
            select(Experiment).where(Experiment.experiment_fingerprint == experiment_fp)
        )
        if existing is not None:
            raise DuplicateExperimentError(f"experiment already exists: {existing.id}")

        strategy_fp = strategy_fingerprint(config.strategy_family, config.strategy_config)
        strategy = db.scalar(
            select(Strategy).where(Strategy.strategy_family == config.strategy_family)
        )
        if strategy is None:
            strategy = Strategy(
                name=config.strategy_family,
                description=f"Deterministic {config.strategy_family} strategy",
                strategy_family=config.strategy_family,
                status=StrategyStatus.ACTIVE,
            )
            db.add(strategy)
            db.flush()

        version = db.scalar(
            select(StrategyVersion).where(StrategyVersion.fingerprint == strategy_fp)
        )
        if version is None:
            latest = db.scalar(
                select(StrategyVersion.version)
                .where(StrategyVersion.strategy_id == strategy.id)
                .order_by(StrategyVersion.version.desc())
                .limit(1)
            )
            version = StrategyVersion(
                strategy_id=strategy.id,
                version=(latest or 0) + 1,
                fingerprint=strategy_fp,
                config=config.strategy_config,
                hypothesis=config.hypothesis,
                parent_experiment_id=(
                    uuid.UUID(config.parent_experiment_id)
                    if config.parent_experiment_id
                    else None
                ),
                generation=config.generation,
            )
            db.add(version)
            db.flush()

        lineage_fp = lineage_fingerprint(
            session_id=session_id,
            experiment_id=None,
            parent_experiment_id=(
                uuid.UUID(config.parent_experiment_id) if config.parent_experiment_id else None
            ),
            generation=config.generation,
            strategy_fingerprint=strategy_fp,
            dataset_fingerprint_value=dataset_fingerprint,
        )
        experiment = Experiment(
            session_id=session_id,
            strategy_version_id=version.id,
            parent_experiment_id=(
                uuid.UUID(config.parent_experiment_id) if config.parent_experiment_id else None
            ),
            generation=config.generation,
            status=ExperimentStatus.QUEUED,
            parameters=config.parameters(),
            dataset_config=config.dataset_config(),
            experiment_fingerprint=experiment_fp,
            dataset_fingerprint=dataset_fingerprint,
            lineage_fingerprint=lineage_fp,
            engine_version=config.engine_version,
        )
        db.add(experiment)
        db.commit()
        db.refresh(experiment)
        return experiment

    def start(self, db: Session, experiment_id: uuid.UUID) -> Experiment:
        experiment = self._get(db, experiment_id)
        if experiment.status != ExperimentStatus.QUEUED:
            raise ValueError(f"experiment cannot start from status {experiment.status.value}")
        experiment.status = ExperimentStatus.RUNNING
        experiment.started_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(experiment)
        return experiment

    def complete(
        self,
        db: Session,
        experiment_id: uuid.UUID,
        *,
        metrics: dict,
        equity_curve: dict,
        trade_count: int,
        total_return: Decimal,
        max_drawdown: Decimal,
    ) -> Experiment:
        experiment = self._get(db, experiment_id)
        if experiment.status != ExperimentStatus.RUNNING:
            raise ValueError(
                f"experiment cannot complete from status {experiment.status.value}"
            )
        if experiment.result is not None:
            raise ValueError("experiment already has a backtest result")

        db.add(
            BacktestResult(
                experiment_id=experiment.id,
                metrics=metrics,
                equity_curve=equity_curve,
                trade_count=trade_count,
                total_return=total_return,
                max_drawdown=max_drawdown,
            )
        )
        experiment.status = ExperimentStatus.COMPLETED
        experiment.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(experiment)
        return experiment

    def fail(self, db: Session, experiment_id: uuid.UUID, error: str) -> Experiment:
        experiment = self._get(db, experiment_id)
        if experiment.status not in {ExperimentStatus.QUEUED, ExperimentStatus.RUNNING}:
            raise ValueError(f"experiment cannot fail from status {experiment.status.value}")
        experiment.status = ExperimentStatus.FAILED
        experiment.error = error
        experiment.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(experiment)
        return experiment

    @staticmethod
    def _get(db: Session, experiment_id: uuid.UUID) -> Experiment:
        experiment = db.get(Experiment, experiment_id)
        if experiment is None:
            raise ValueError(f"experiment not found: {experiment_id}")
        return experiment
