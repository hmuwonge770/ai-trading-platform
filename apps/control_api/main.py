from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from packages.database.session import get_db
from packages.promotion.domain import ApprovalRole, CapitalAllocation, PromotionStage, StrategyVersion, sha256_hex
from packages.promotion.repository import PromotionRepository
from packages.promotion.service import PromotionService

app = FastAPI(title="AI Trading Control API", version="0.2.0")
service = PromotionService()


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


class AuthorizationRequest(BaseModel):
    risk_policy_fingerprint: str = Field(min_length=64, max_length=64)
    ttl_minutes: int = Field(default=15, ge=1, le=60)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "control-api"}


@app.post("/promotions")
def create_promotion(request: PromotionRequest, db: Session = Depends(get_db)):
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
        PromotionRepository(db).create(promotion)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Strategy version or promotion already exists") from exc
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"promotion_id": str(promotion.promotion_id), "status": promotion.status}


@app.get("/promotions/{promotion_id}")
def get_promotion(promotion_id: UUID, db: Session = Depends(get_db)):
    promotion = PromotionRepository(db).get(promotion_id)
    if promotion is None:
        raise HTTPException(status_code=404, detail="Promotion not found")
    return {
        "promotion_id": str(promotion.promotion_id),
        "strategy_version_id": str(promotion.strategy_version.strategy_version_id),
        "strategy_fingerprint": promotion.strategy_version.fingerprint,
        "from_stage": promotion.from_stage,
        "to_stage": promotion.to_stage,
        "requested_by": promotion.requested_by,
        "status": promotion.status,
        "approvals": len(promotion.approvals),
        "required_approvals": promotion.required_approvals,
    }


@app.post("/promotions/{promotion_id}/approve")
def approve_promotion(promotion_id: UUID, request: ApprovalRequest, db: Session = Depends(get_db)):
    repo = PromotionRepository(db)
    promotion = repo.get(promotion_id)
    if promotion is None:
        raise HTTPException(status_code=404, detail="Promotion not found")
    try:
        result = repo.add_approval(
            promotion_id,
            approver_id=request.approver_id,
            role=request.role,
            capital_limit=request.capital_limit,
            evidence_hash=sha256_hex(request.evidence),
            fingerprint=promotion.strategy_version.fingerprint,
        )
    except (ValueError, PermissionError) as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Approver has already acted on this promotion") from exc
    return {"promotion_id": str(promotion_id), "status": result.status}


@app.post("/promotions/{promotion_id}/activate")
def activate_promotion(promotion_id: UUID, db: Session = Depends(get_db)):
    try:
        promotion = PromotionRepository(db).activate(promotion_id)
    except LookupError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, PermissionError) as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"promotion_id": str(promotion_id), "status": promotion.status}


@app.post("/promotions/{promotion_id}/authorization")
def create_authorization(promotion_id: UUID, request: AuthorizationRequest, db: Session = Depends(get_db)):
    repo = PromotionRepository(db)
    promotion = repo.get(promotion_id)
    if promotion is None:
        raise HTTPException(status_code=404, detail="Promotion not found")
    try:
        snapshot = service.authorization(
            promotion,
            risk_policy_fingerprint=request.risk_policy_fingerprint,
            ttl=timedelta(minutes=request.ttl_minutes),
        )
        repo.save_authorization(snapshot)
    except (ValueError, PermissionError) as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "promotion_id": str(promotion_id),
        "authorization_hash": snapshot.authorization_hash,
        "environment": snapshot.environment,
        "expires_at": snapshot.expires_at,
    }


@app.post("/promotions/{promotion_id}/halt")
def halt_promotion(promotion_id: UUID, db: Session = Depends(get_db)):
    try:
        promotion = PromotionRepository(db).halt(promotion_id)
    except LookupError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"promotion_id": str(promotion_id), "status": promotion.status}
