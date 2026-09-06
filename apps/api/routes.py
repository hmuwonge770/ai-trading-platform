from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.database.models import Experiment, MarketCandle, ResearchSession
from packages.database.session import get_db
from packages.experiments.manager import DuplicateExperimentError, ExperimentManager
from packages.experiments.models import ExperimentConfig

from apps.api.schemas import (
    CandleResponse,
    ExperimentCreate,
    ExperimentResponse,
    ResearchSessionCreate,
    ResearchSessionResponse,
)

router = APIRouter(prefix="/api/v1", tags=["research"])
manager = ExperimentManager()


@router.post(
    "/research-sessions",
    response_model=ResearchSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_research_session(
    request: ResearchSessionCreate,
    db: Session = Depends(get_db),
) -> ResearchSession:
    session = ResearchSession(
        name=request.name,
        objective=request.objective,
        config=request.config,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get(
    "/research-sessions/{session_id}",
    response_model=ResearchSessionResponse,
)
def get_research_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ResearchSession:
    session = db.get(ResearchSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="research session not found")
    return session


@router.get(
    "/research-sessions/{session_id}/experiments",
    response_model=list[ExperimentResponse],
)
def list_session_experiments(
    session_id: uuid.UUID,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[Experiment]:
    if db.get(ResearchSession, session_id) is None:
        raise HTTPException(status_code=404, detail="research session not found")

    statement = (
        select(Experiment)
        .where(Experiment.session_id == session_id)
        .order_by(Experiment.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(statement).all())


@router.post(
    "/research-sessions/{session_id}/experiments",
    response_model=ExperimentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_experiment(
    session_id: uuid.UUID,
    request: ExperimentCreate,
    db: Session = Depends(get_db),
) -> Experiment:
    if db.get(ResearchSession, session_id) is None:
        raise HTTPException(status_code=404, detail="research session not found")

    try:
        config = ExperimentConfig(
            session_id=str(session_id),
            strategy_family=request.strategy_family,
            strategy_config=request.strategy_config,
            symbol=request.symbol,
            timeframe=request.timeframe,
            start_time=request.start_time,
            end_time=request.end_time,
            initial_capital=request.initial_capital,
            fee_rate=request.fee_rate,
            slippage_rate=request.slippage_rate,
            dataset_split=request.dataset_split,
            engine_version=request.engine_version,
            hypothesis=request.hypothesis,
            generation=request.generation,
            parent_experiment_id=(
                str(request.parent_experiment_id) if request.parent_experiment_id else None
            ),
        )
        return manager.create(db, config)
    except DuplicateExperimentError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/experiments/{experiment_id}", response_model=ExperimentResponse)
def get_experiment(
    experiment_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> Experiment:
    experiment = db.get(Experiment, experiment_id)
    if experiment is None:
        raise HTTPException(status_code=404, detail="experiment not found")
    return experiment


@router.get(
    "/market-data/{symbol}/{timeframe}/candles",
    response_model=list[CandleResponse],
)
def get_candles(
    symbol: str,
    timeframe: str,
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[MarketCandle]:
    normalized_symbol = symbol.strip().upper()
    normalized_timeframe = timeframe.strip().upper()
    statement = (
        select(MarketCandle)
        .where(
            MarketCandle.symbol == normalized_symbol,
            MarketCandle.timeframe == normalized_timeframe,
        )
        .order_by(MarketCandle.open_time.desc())
        .limit(limit)
    )
    return list(reversed(db.scalars(statement).all()))
