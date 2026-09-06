from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from packages.backtesting.engine import BacktestEngine
from packages.database.models import Experiment
from packages.experiments.manager import ExperimentManager
from packages.experiments.models import ExperimentConfig
from packages.strategies.models import MarketBar
from packages.strategies.registry import build_strategy


class ExperimentRunner:
    """Run only the training partition and persist its deterministic result.

    Validation and final-test partitions are deliberately not consumed here.
    They belong to later validation/promotion stages and must remain unseen by
    parameter selection.
    """

    def __init__(self, manager: ExperimentManager | None = None) -> None:
        self.manager = manager or ExperimentManager()
        self.engine = BacktestEngine()

    def run(
        self,
        db: Session,
        config: ExperimentConfig,
        candles: Sequence[MarketBar],
    ) -> Experiment:
        if len(candles) < 3:
            raise ValueError("at least three candles are required for train/validation/test")
        self._validate_candle_range(config, candles)

        experiment = self.manager.create(db, config)
        self.manager.start(db, experiment.id)

        try:
            train, _, _ = self.split_candles(candles, config)
            if not train:
                raise ValueError("training partition is empty")
            strategy = build_strategy(config.strategy_family, config.strategy_config)
            result = self.engine.run(
                train,
                strategy,
                config.initial_capital,
                fee_rate=config.fee_rate,
                slippage_rate=config.slippage_rate,
            )
            return self.manager.complete(
                db,
                experiment.id,
                metrics={
                    "initial_capital": str(result.initial_capital),
                    "final_equity": str(result.final_equity),
                    "total_fees": str(result.total_fees),
                    "winning_trades": result.winning_trades,
                    "losing_trades": result.losing_trades,
                    "win_rate": str(result.win_rate),
                },
                equity_curve={
                    "points": [
                        {
                            "time": point.time.isoformat(),
                            "equity": str(point.equity),
                            "cash": str(point.cash),
                            "position_value": str(point.position_value),
                        }
                        for point in result.equity_curve
                    ]
                },
                trade_count=len(result.trades),
                total_return=result.total_return,
                max_drawdown=result.max_drawdown,
            )
        except Exception as exc:
            self.manager.fail(db, experiment.id, str(exc))
            raise

    @staticmethod
    def split_candles(
        candles: Sequence[MarketBar], config: ExperimentConfig
    ) -> tuple[tuple[MarketBar, ...], tuple[MarketBar, ...], tuple[MarketBar, ...]]:
        total = len(candles)
        if total < 3:
            raise ValueError("at least three candles are required for train/validation/test")
        train_count = max(1, int(total * config.dataset_split.train))
        validation_count = max(1, int(total * config.dataset_split.validation))
        if train_count + validation_count >= total:
            train_count = max(1, total - 2)
            validation_count = 1
        return (
            tuple(candles[:train_count]),
            tuple(candles[train_count : train_count + validation_count]),
            tuple(candles[train_count + validation_count :]),
        )

    @staticmethod
    def _validate_candle_range(config: ExperimentConfig, candles: Sequence[MarketBar]) -> None:
        if any(
            candle.symbol != config.symbol or candle.timeframe != config.timeframe
            for candle in candles
        ):
            raise ValueError("all candles must match the experiment symbol and timeframe")
        if candles[0].open_time < config.start_time or candles[-1].open_time >= config.end_time:
            raise ValueError("candles fall outside the configured experiment window")
        for index in range(1, len(candles)):
            if candles[index].open_time <= candles[index - 1].open_time:
                raise ValueError("candles must be strictly ordered")
