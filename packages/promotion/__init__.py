"""Strategy promotion and live authorization domain."""

from .canary import CanaryController, CanaryLimits, CanaryState
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
from .invalidation import AuthorizationBinding, AuthorizationValidator
from .preflight import LivePreflight, PreflightContext, PreflightResult
from .repository import PromotionRepository
from .service import PromotionService

__all__ = [
    "ApprovalDecision", "ApprovalRole", "AuthorizationSnapshot", "CapitalAllocation",
    "Promotion", "PromotionRepository", "PromotionService", "PromotionStage", "PromotionStatus", "StrategyVersion",
    "CanaryController", "CanaryLimits", "CanaryState", "AuthorizationBinding", "AuthorizationValidator",
    "LivePreflight", "PreflightContext", "PreflightResult",
]
