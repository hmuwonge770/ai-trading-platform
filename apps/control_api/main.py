from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from packages.promotion.domain import ApprovalRole, CapitalAllocation, PromotionStage, StrategyVersion
from packages.promotion.service import PromotionService

app = FastAPI(title="AI Trading Control API", version="0.1.0")
service = PromotionService()
# Temporary process-local registry for the bootstrap. Replace with PostgreSQL repository in the persistence slice.
promotions = {}


class PromotionRequest(BaseModel):
    strategy_version_id: UUID
    strategy_id: UUID
    fingerprint: str = Field(min_length=64, max_length=64)
    configuration: dict
    from_stage: PromotionStage
    to_stage: PromotionStage
    requested_by: str = Field(min_length=1)
    max_capital: Decimal = Field(gt=0)
    max_position_value: Decimal = Field(gt=0)
    max_daily_loss: Decimal = Field(gt=0)
    max_orders_per_day: int = Field(gt=0)


class ApprovalRequest(BaseModel):
    approver_id: str = Field(min_length=1)
    role: ApprovalRole
    capital_limit: Decimal = Field(gt=0)
    evidence: dict = Field(default_factory=dict)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "control-api"}


@app.post("/promotions")
def create_promotion(request: PromotionRequest):
    try:
        promotion = service.request(
            strategy_version=StrategyVersion(
                strategy_version_id=request.strategy_version_id,
                strategy_id=request.strategy_id,
                fingerprint=request.fingerprint,
                configuration=request.configuration,
            ),
            from_stage=request.from_stage,
            to_stage=request.to_stage,
            requested_by=request.requested_by,
            capital_allocation=CapitalAllocation(
                environment=request.to_stage,
                max_capital=request.max_capital,
                max_position_value=request.max_position_value,
                max_daily_loss=request.max_daily_loss,
                max_orders_per_day=request.max_orders_per_day,
            ),
            evidence={"configuration": request.configuration},
        )
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    promotions[promotion.promotion_id] = promotion
    return {"promotion_id": str(promotion.promotion_id), "status": promotion.status}


@app.post("/promotions/{promotion_id}/approve")
def approve_promotion(promotion_id: UUID, request: ApprovalRequest):
    promotion = promotions.get(promotion_id)
    if promotion is None:
        raise HTTPException(status_code=404, detail="Promotion not found")
    try:
        service.approve(
            promotion,
            approver_id=request.approver_id,
            role=request.role,
            capital_limit=request.capital_limit,
            evidence=request.evidence,
        )
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"promotion_id": str(promotion_id), "status": promotion.status}


@app.post("/promotions/{promotion_id}/activate")
def activate_promotion(promotion_id: UUID):
    promotion = promotions.get(promotion_id)
    if promotion is None:
        raise HTTPException(status_code=404, detail="Promotion not found")
    try:
        service.activate(promotion)
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"promotion_id": str(promotion_id), "status": promotion.status}


@app.post("/promotions/{promotion_id}/halt")
def halt_promotion(promotion_id: UUID):
    promotion = promotions.get(promotion_id)
    if promotion is None:
        raise HTTPException(status_code=404, detail="Promotion not found")
    try:
        service.halt(promotion)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"promotion_id": str(promotion_id), "status": promotion.status}
