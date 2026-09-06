"""Strategy promotion and live authorization domain."""

from .domain import (
    ApprovalDecision,
    ApprovalRole,
    AuthorizationSnapshot,
    CapitalAllocation,
    Promotion,
    PromotionStage,
    PromotionStatus,
    StrategyVersion,
)
from .service import PromotionService
from .preflight import LivePreflight, PreflightContext, PreflightResult

__all__ = [
    "ApprovalDecision",
    "ApprovalRole",
    "AuthorizationSnapshot",
    "CapitalAllocation",
    "Promotion",
    "PromotionService",
    "PromotionStage",
    "PromotionStatus",
    "StrategyVersion",
    "LivePreflight",
    "PreflightContext",
    "PreflightResult",
]
